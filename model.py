from sqlalchemy import func
from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy
db = SQLAlchemy()


class Transaction(db.Model):
    tx_id = db.Column(db.Integer, primary_key=True)
    gasPrice = db.Column(db.Integer)
    gas = db.Column(db.Integer)
    tx_type = db.Column(db.Integer)
    hash = db.Column(db.String(50))
    value = db.Column(db.Integer)
    addr_to = db.Column(db.String(50))
    addr_from = db.Column(db.String(50))
    maxPriorityFeePerGas = db.Column(db.Integer)
    block_id = db.Column(db.Integer, db.ForeignKey('block.number'))
    fee = db.Column(db.Integer)

    def __init__(self, hash, addr_from, addr_to, value, tx_type, gas, gasPrice, maxPriorityFeePerGas):
        self.maxPriorityFeePerGas = maxPriorityFeePerGas
        self.hash = hash
        self.gasPrice = gasPrice
        self.gas = gas
        self.tx_type = tx_type
        self.value = value
        self.addr_to = addr_to
        self.addr_from = addr_from
        self.fee = self.gas * self.gasPrice


class Block(db.Model):
    number = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.Integer)
    size = db.Column(db.String(50))
    miner = db.Column(db.String(50))
    blockHash = db.Column(db.String(50))
    parentHash = db.Column(db.String(50))
    gasUsed = db.Column(db.Integer)
    gasLimit = db.Column(db.Integer)
    baseFeePerGas = db.Column(db.Integer)
    averageFee = db.Column(db.Integer)
    transactionCount = db.Column(db.Integer)
    transactions = db.relationship('Transaction', backref='block', cascade="all, delete-orphan",
                                   lazy='dynamic')

    def __init__(self, number, baseFeePerGas, gasLimit, gasUsed, blockHash, miner,
                 parentHash, size, timestamp, transactionCount):
        self.number = number
        self.timestamp = timestamp
        self.size = size
        self.miner = miner
        self.blockHash = blockHash
        self.parentHash = parentHash
        self.gasUsed = gasUsed
        self.gasLimit = gasLimit
        self.baseFeePerGas = baseFeePerGas
        self.transactionCount = transactionCount

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Block_hist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.Integer)
    gasUsed = db.Column(db.Integer)
    gasLimit = db.Column(db.Integer)
    averageFee = db.Column(db.Integer)
    transactions = db.Column(db.Integer)

    def __init__(self, time, gasUsed, gasLimit, averageFee, transactions):
        self.time = time
        self.gasUsed = gasUsed
        self.gasLimit = gasLimit
        self.averageFee = averageFee
        self.transactions = transactions
