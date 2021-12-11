import datetime
from flask import Flask, render_template, jsonify
from flask_apscheduler import APScheduler
from sqlalchemy import func
import os
#import json

from model import *
from evmos_util import *


# Init App and Database Databsase
app = Flask(__name__)
if os.environ['FLASK_ENV'] == 'development':
    print('THIS APP IS IN DEBUG MODE.')
    app.config.from_object("config.DevelopmentConfig")
else:
    app.config.from_object("config.ProductionConfig")
db.app = app
db.init_app(app)
db.create_all()
db.engine.dispose()
# Lösung aus https://stackoverflow.com/questions/22752521/uwsgi-flask-sqlalchemy-and-postgres-ssl-error-decryption-failed-or-bad-reco

# APScheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()


def db_lastblock():
    db_block = db.session.query(Block).order_by(Block.number.desc()).first()
    return db_block


def db_createblock(blockheight):
    response = eth_getblock_data(blockheight)
    number = hex_to_int(response['number'])
    baseFeePerGas = hex_to_int(response['baseFeePerGas'])
    gasLimit = hex_to_int(response['gasLimit'])
    gasUsed = hex_to_int(response['gasUsed'])
    blockHash = response['hash']
    miner = response['miner']
    parentHash = response['parentHash']
    size = hex_to_int(response['size'])
    timestamp = hex_to_int(response['timestamp'])
    transactionCount = len(response['transactions'])
    blockValue = Block(number=number, baseFeePerGas=baseFeePerGas, gasLimit=gasLimit, gasUsed=gasUsed,
                       blockHash=blockHash, miner=miner, parentHash=parentHash, size=size, timestamp=timestamp,
                       transactionCount=transactionCount)
    for transaction in response['transactions']:
        addr_from = transaction['from']
        addr_to = transaction['to']
        value = hex_to_int(transaction['value'])
        tx_type = hex_to_int(transaction['type'])
        gas = hex_to_int(transaction['gas'])
        hash = transaction['hash']
        gasPrice = hex_to_int(transaction['gasPrice'])
        if 'maxPriorityFeePerGas' in transaction.keys():
            maxPriorityFeePerGas = hex_to_int(transaction['maxPriorityFeePerGas'])
        else:
            maxPriorityFeePerGas = 0
        transactionValue = Transaction(hash=hash, addr_from=addr_from, addr_to=addr_to, value=value, tx_type=tx_type, gas=gas,
                                       gasPrice=gasPrice, maxPriorityFeePerGas=maxPriorityFeePerGas)
        blockValue.transactions.append(transactionValue)
        db.session.add(transactionValue)
    feelist =[x.fee for x in blockValue.transactions.all()]
    if len(feelist) > 0:
        blockValue.averageFee = sum(feelist)/len(feelist)
    else:
        blockValue.averageFee = 0
    db.session.add(blockValue)
    db.session.commit()


def db_update():
    eth_block = eth_currentblock_number()
    db_block = db_lastblock()
    if db_block is None:
        db_block = 0
    else:
        db_block = db_block.number
    if eth_block > db_block:
        if eth_block > db_block + 120:
            db_block = eth_block - 120
        for block in range(db_block+1, eth_block):
            db_createblock(block)
            print(f"{block} has been written to DB")
    else:
        print("DB has heighest block")

# TODO Delete Transactions older then 7 days
def db_deleteoldblocks(olderthentimestamp):
    # TODO UTC Zeitverschiebung prüfen
    oldBlocks = Block.query.filter(Block.timestamp < olderthentimestamp).all()
    for block in oldBlocks:
        db.session.delete(block)
    db.session.commit()
    print(f"Older then {datetime.datetime.fromtimestamp(olderthentimestamp)} deleted from DB")
    db.session.commit()


def db_copytohist(timestamp_from, timestamp_to):
    hist_blocks = db.session.query(
        func.max(Block.transactionCount).label("sum_transactions"),
        func.avg(Block.averageFee).label("avg_fee"),
        func.avg(Block.gasUsed).label("avg_gasUsed"),
        func.avg(Block.gasLimit).label("avg_gasLimit"),
    ).filter(Block.timestamp >= timestamp_from, Block.timestamp <= timestamp_to).first()
    if all(block is not None for block in hist_blocks):
        hist_blockValue = Block_hist(
            time=round(timestamp_from, 0),
            transactions=hist_blocks['sum_transactions'],
            gasLimit=hist_blocks['avg_gasLimit'],
            gasUsed=hist_blocks['avg_gasUsed'],
            averageFee=hist_blocks['avg_fee']
        )
        db.session.add(hist_blockValue)
        db.session.commit()

def db_averageGas(numberofblock):
    blocks = db.session.query(Block).order_by(Block.number.desc()).limit(numberofblock).all()
    feelist = []
    for block in blocks:
        if block.averageFee is None:
            feelist.append(block.baseFeePerGas)
        elif block.gasLimit - block.gasUsed > 21000:
            feelist.append(block.baseFeePerGas)
        else:
            feelist.append(block.averageFee)
    return int(sum(feelist)/len(feelist))


@scheduler.task('interval', id='job_dbupdate', seconds=10, misfire_grace_time=30)
def job_dbupdate():
    db_update()

# TODO Bug richtig fixen
@scheduler.task('cron', id='job_rollbackb', minute='*/5')
def job_rollback():
    db.session.rollback()


@scheduler.task('cron', id='job_cleandb', minute='*/10')
def clean_db():
    timestamp_to = round(datetime.datetime.now().timestamp(), 0)
    timestamp_from = timestamp_to - 600
    db_copytohist(timestamp_from, timestamp_to)
    db_deleteoldblocks(timestamp_from)


# TODO Vorbefüllen mit aktuellen Werten damit es beim Laden nicht ploppt
# TODO Hinweis auf Website, wenn der letzte Zeitstempel länger als 10 Minuten entfernt
# TODO Hinweis wenn der RPC nicht reagiert
@app.route('/')
def index():
    time = []
    transactions = []
    histdata = db.session.query(Block_hist).all()
    if datetime.datetime.now().timestamp() >= db_lastblock().timestamp + 600:
        warning = "Error in synchronisation"
    else:
        warning = None
    for data in histdata:
       time.append(data.time * 1000)
       transactions.append(data.transactions)
    return render_template(
        "index.html",
        #blockstatus=json.dumps(block_status().response),
        time=time,
        tx_data=transactions,
        warning=warning
    )

# TODO TailwindCSS 3.0
# TODO Tailwind Deploy Automation
# TODO Block Time berechnen um nicht 9 Sekunden pro Block statisch auszugeben
@app.route('/blockstatus', methods=['POST'])
def block_status():
    transactionGas = 21000
    try:
        data = db_lastblock()
        if data is not None:
            data = data.as_dict()
        data['timestamp_str'] = datetime.datetime.fromtimestamp(data['timestamp']).strftime('%Y/%m/%d %H:%M:%S')
        for i in [1, 6, 20]:
            data[f'gas_avgFee_{i}'] = db_averageGas(i)
            data[f'gas_transactionPrice_{i}'] = data[f'gas_avgFee_{i}'] * transactionGas
    except:
        data = []
    return jsonify(data)


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)




#Informationen: Aktuelle Blocknummer, Zeitstempel des Blockes, GasUsed, GasLimit, set gas_price
#Wenn Block noch nicht voll, dann kann der standardgaspreis genommen werden.
#Wenn Block voll, dann:
#Icon (Rakete, Auto, Spazieren, Schnecke), photon, in euro
#Instant = min of last block
#fast 27 sec = min of last 3 blocks (3*9)
#medium 54 sec = min of last 6 blocks (6*9)
#slow 180 sec = min of last 6 blocks (6*9)

#Timeline
#average gas us per block in history

#heatmap
#average gas price per day and time

#transaction by gas price in the last hour (Balkendiagramm)

#Heatmap
#speed


#current_gasestimation = eth_estimateGas('0xCF292488f71DceDDDde12c34C654409096801afC', '0x2B3EA71489855C524E193cFA7E95F2F2825CE2A8', "0x16345785d8a00000")