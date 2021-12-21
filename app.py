from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_apscheduler import APScheduler
from sqlalchemy import func, desc, text
import os, math, calendar, datetime

from model import *
from evmos_util import *


# Variable
SYNC_NUMBER = 93000  #one Week

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
        blockValue.averageFee = None
    gaspricelist = [x.gasPrice * x.gas for x in blockValue.transactions.all()]
    total_gas = [x.gas for x in blockValue.transactions.all()]
    if len(gaspricelist) > 0:
        blockValue.averageGasPrice = sum(gaspricelist)/sum(total_gas)
    else:
        blockValue.averageGasPrice = None
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
        # TODO Prüfen von wann an
        if eth_block > db_block + SYNC_NUMBER:
            db_block = eth_block - SYNC_NUMBER
        for block in range(db_block+1, eth_block):
            db_createblock(block)
            print(f"Block {block} --> db.block")
    else:
        print("db.block has heighest block")


def db_deleteoldblocks(olderthentimestamp):
    # TODO UTC Zeitverschiebung prüfen
    oldBlocks = Block.query.filter(Block.timestamp < olderthentimestamp).all()
    for block in oldBlocks:
        db.session.delete(block)
    db.session.commit()
    print(f"Block < {datetime.datetime.fromtimestamp(olderthentimestamp)} deleted --> db.block")
    db.session.commit()


def db_deleteoldhistblocks(olderthentimestamp):
    # TODO UTC Zeitverschiebung prüfen
    oldBlocks = Block_hist.query.filter(Block_hist.time < olderthentimestamp).all()
    for block in oldBlocks:
        db.session.delete(block)
    db.session.commit()
    print(f"Block < {datetime.datetime.fromtimestamp(olderthentimestamp)} deleted --> db.block_history")
    db.session.commit()


def db_copytohist(timestamp_from, timestamp_to):
    hist_blocks = db.session.query(
        func.sum(Block.transactionCount).label("sum_transactions"),
        func.avg(Block.averageFee).label("avg_fee"),
        func.avg(Block.gasUsed).label("avg_gasUsed"),
        func.avg(Block.gasLimit).label("avg_gasLimit"),
        func.avg(Block.averageGasPrice).label("avg_gasPrice"),
        func.sum(Block.averageGasPrice).label("sum_gasPrice"),
    ).filter(Block.timestamp >= timestamp_from, Block.timestamp <= timestamp_to).first()
    hist_blockValue = Block_hist(
        time=round(timestamp_from, 0),
        transactions=hist_blocks['sum_transactions'],
        gasLimit=hist_blocks['avg_gasLimit'],
        gasUsed=hist_blocks['avg_gasUsed'],
        averageFee=hist_blocks['avg_fee'],
        averageGasPrice=hist_blocks['avg_gasPrice'],
        sumGasPrice=hist_blocks['sum_gasPrice']
    )
    db.session.add(hist_blockValue)
    print(f"db.block >= {timestamp_from} and <= {timestamp_to} --> db.block_hist")
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


def price_matrix():
    today_date = datetime.date.today() + datetime.timedelta(days=1)
    past_7_date = today_date - datetime.timedelta(days=8)
    today_timestamp = datetime.datetime.strptime(today_date.strftime("%d.%m.%Y"), "%d.%m.%Y").timestamp()
    past_7_timestamp = datetime.datetime.strptime(past_7_date.strftime("%d.%m.%Y"), "%d.%m.%Y").timestamp()

    blocks = db.session.query(
        func.date_part('day', func.to_timestamp(Block_hist.time)).label('day'),
        func.date_part('hour', func.to_timestamp(Block_hist.time)).label('hour'),
        func.sum(Block_hist.sumGasPrice).label('sumGasPrice'),
        func.sum(Block_hist.transactions).label('sumTransactions'),
        func.min(Block_hist.time).label('timestamp'),
    ).filter(
        Block_hist.time >= past_7_timestamp,
        Block_hist.time < today_timestamp
    ).group_by('day', 'hour').all()

    data = {}
    hours = [str(i).zfill(2)+":00" for i in range(24)]
    # rearrange Week List to today
    days = [day for day in calendar.day_name]
    pos = days.index(calendar.day_name[datetime.datetime.today().weekday()]) + 1
    days = days[pos:] + days[:pos]

    # Create DF
    for hour in hours:
        data[hour] = {}
        for day in calendar.day_name:
            data[hour][day] = {}
            data[hour][day]["value"] = ""
            data[hour][day]["color"] = 0

    max_avgGasPrice = max([block.sumGasPrice/block.sumTransactions for block in blocks if block.sumGasPrice is not None], default=0)/1000000

    # Fill DF
    for block in blocks:
        if block.sumGasPrice is None:
            value = "-"
            color = 0
        else:
            value = round((block.sumGasPrice/block.sumTransactions)/1000000)
            color = (round(9 - value / max_avgGasPrice * 4))*100
        current_hour = str(int(block.hour)).zfill(2) + ":00"
        # Timestamp minus 60 Minutes because of UTC Time of the rest of the Query
        current_day = calendar.day_name[datetime.datetime.fromtimestamp(block.timestamp-60*60).weekday()]
        data[current_hour][current_day]["value"] = value
        data[current_hour][current_day]["color"] = color
        today = datetime.datetime.today()
        if (
                current_hour == (datetime.datetime.now()-datetime.timedelta(hours=1, minutes=10)).strftime("%H:00")
                and
                current_day == calendar.day_name[datetime.datetime.today().weekday()]
        ):
            data[current_hour][current_day]["currentdatetime"] = 1
        else:
            data[current_hour][current_day]["currentdatetime"] = 0

    return data, days, hours


def get_validators():
    url = 'https://evmos-api.mercury-nodes.net/staking/validators'
    res = requests.get(url)
    d = json.loads(res.text)
    return [validator_loader(x) for x in d['result']]


@scheduler.task('interval', id='job_dbupdate', seconds=10, misfire_grace_time=30)
def job_dbupdate():
    db_update()


# TODO Bug richtig fixen
@scheduler.task('cron', id='job_rollbackb', minute='*/5')
def job_rollback():
    db.session.rollback()


@scheduler.task('cron', id='job_cleandb', minute='*/10')
def clean_db():
    # copy all data to hist
    oldest_timestamp = db.session.query(Block).order_by(Block.number.asc()).first().timestamp
    newest_timestamp = db.session.query(Block).order_by(Block.number.desc()).first().timestamp
    oldest_time = datetime.datetime.fromtimestamp(oldest_timestamp)
    timestamp_from = oldest_time.replace(minute=math.floor(oldest_time.minute / 10) * 10, second=0,
                                         microsecond=0).timestamp()
    timestamp_to = timestamp_from + 10 * 60
    while timestamp_to < newest_timestamp:
        # TODO was machen wenn kein hist Block vorhanden?
        db_copytohist(timestamp_from, timestamp_to)
        db_deleteoldblocks(timestamp_to)
        timestamp_from = timestamp_to
        timestamp_to = timestamp_to + 10 * 60
    db_deleteoldhistblocks(timestamp_to - (10 * 24 * 60 * 60))  # Delete hist older than 10 days


@scheduler.task('cron', id='job_validatorupdate', minute='*/30', next_run_time=datetime.datetime.now())
def validator_update():
    print("Updating Validators")
    allvalidators = get_validators()
    maxPower = sum([validator.tokens for validator in allvalidators])
    Validator.query.delete()
    db.session.commit()
    for validator in allvalidators:
        validator.power_share = validator.tokens/maxPower
        db.make_transient(validator)
        db.session.add(validator)
    db.session.commit()
    print("Validators --> db.validator")


@app.route('/validators')
def validators():
    page = request.args.get('page')
    if page is not None and page.isdigit():
        page = int(page)
    else:
        page = 1
    order_by = request.args.get('order_by')
    order_by_list = ['power_share', 'moniker', 'comission_rate', 'self_share']
    if order_by not in order_by_list:
        order_by = order_by_list[0]
    order = request.args.get('order')
    order_list = ['desc', 'asc']
    if order not in order_list:
        order = order_list[0]
    pagenumber = round(len(Validator.query.all())/25)
    maxPower = db.session.query(func.sum(Validator.tokens).label("sum_tokens")).first()
    return render_template(
        "validators.html",
        validators=Validator.query.order_by(text(order_by+" "+order), 'moniker').offset(25 * (page - 1)).limit(25).all(),
        pagenumber=pagenumber,
        page=page,
        order_by=order_by,
        order=order,
        maxPower=maxPower.sum_tokens,
        warning=None
    )


@app.route('/')
def index():
    return redirect(url_for('gas'))


# TODO Vorbefüllen mit aktuellen Werten damit es beim Laden nicht ploppt
# TODO Hinweis wenn der RPC nicht reagiert
# TODO Transactions in the last 24 hours (and tx/seconds)
# TODO Average Gas Price last 24 Hours
@app.route('/gas')
def gas():
    time = []
    transactions = []
    matrix, days, hours = price_matrix()
    histdata = db.session.query(Block_hist).filter(Block_hist.time > datetime.datetime.now().timestamp() - (60*60*24)).order_by(Block_hist.time.desc()).all()
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
        matrix=matrix,
        days=days,
        hours=hours,
        warning=warning
    )

# TODO Tailwind Deploy Automation
# TODO Block Time berechnen um nicht 9 Sekunden pro Block statisch auszugeben
@app.route('/blockstatus', methods=['POST', 'GET'])
def block_status():
    #try:
    data = db_lastblock()
    if data is not None:
        data = data.as_dict()
    data['timestamp_str'] = datetime.datetime.fromtimestamp(data['timestamp']).strftime('%Y/%m/%d %H:%M:%S')
    averageGas = {}
    blocks = [1, 6, 20]
    for count, i in enumerate(blocks):
        averageGas[i] = db_averageGas(i)
        if count > 1 and averageGas[i] > averageGas[blocks[count-1]]:
            averageGas[i] = averageGas[blocks[count-1]]
    data['gas_avgFee'] = averageGas
    hist_transactions = db.session.query(
        func.sum(Block_hist.transactions).label("sum_transactions"),
        func.sum(Block_hist.sumGasPrice).label("sum_gasprice")
    ).filter(
        Block_hist.time >= (datetime.datetime.now().timestamp() - 24 * 60 * 60)
    ).first()
    data['hist_sum_tx'] = 0 if hist_transactions['sum_transactions'] is None else hist_transactions['sum_transactions']
    if data['hist_sum_tx'] == 0:
        data['hist_avg_fee'] = 0
    else:
        data['hist_avg_fee'] = 0 if hist_transactions['sum_gasprice'] is None else hist_transactions['sum_gasprice']/hist_transactions['sum_transactions']
    #except:
    #data = []
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

# postgres_session.query(
#         func.date_part('day', func.to_timestamp(Score.timestamp)).label('day'),
#         func.date_part('hour', func.to_timestamp(Score.timestamp)).label('hour'),
#         func.date_part('minute', func.to_timestamp(Score.timestamp)).label('minute'),
#
#         func.max(Score.points).label('points'))
#     .group_by(
#         'day', 'hour', 'minute'
#     )

#gruppe = db.session.query(func.date_part('hour', func.to_timestamp(Block_hist.time)).label('hour')).all()
#db.session.query(extract('hour', Block_hist.time).label('h')).group_by('h').first()
#gruppe = db.session.query(Block_hist).group_by(func.date_trunc('hour', Block_hist.time).label('hour'))
#current_gasestimation = eth_estimateGas('0xCF292488f71DceDDDde12c34C654409096801afC', '0x2B3EA71489855C524E193cFA7E95F2F2825CE2A8', "0x16345785d8a00000")