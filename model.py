from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy
db = SQLAlchemy()


class Transaction(db.Model):
    tx_id = db.Column(db.BIGINT, primary_key=True)
    gasPrice = db.Column(db.BIGINT)
    gas = db.Column(db.BIGINT)
    tx_type = db.Column(db.BIGINT)
    hash = db.Column(db.String(100))
    value = db.Column(db.BIGINT)
    addr_to = db.Column(db.String(100))
    addr_from = db.Column(db.String(100))
    maxPriorityFeePerGas = db.Column(db.BIGINT)
    block_id = db.Column(db.BIGINT, db.ForeignKey('block.number'))
    fee = db.Column(db.BIGINT)

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
    number = db.Column(db.BIGINT, primary_key=True)
    timestamp = db.Column(db.BIGINT)
    size = db.Column(db.String(100))
    miner = db.Column(db.String(100))
    blockHash = db.Column(db.String(100))
    parentHash = db.Column(db.String(100))
    gasUsed = db.Column(db.BIGINT)
    gasLimit = db.Column(db.BIGINT)
    baseFeePerGas = db.Column(db.BIGINT)
    averageFee = db.Column(db.BIGINT)
    transactionCount = db.Column(db.BIGINT)
    averageGasPrice = db.Column(db.BIGINT)
    transactions = db.relationship('Transaction', backref='block', cascade='all,delete', lazy='dynamic')

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
    id = db.Column(db.BIGINT, primary_key=True)
    time = db.Column(db.BIGINT)
    gasUsed = db.Column(db.BIGINT)
    gasLimit = db.Column(db.BIGINT)
    averageFee = db.Column(db.BIGINT)
    averageGasPrice = db.Column(db.BIGINT)
    sumGasPrice = db.Column(db.BIGINT)
    transactions = db.Column(db.BIGINT)

    def __init__(self, time, gasUsed, gasLimit, averageFee, averageGasPrice, sumGasPrice, transactions):
        self.time = time
        self.gasUsed = gasUsed
        self.gasLimit = gasLimit
        self.averageFee = averageFee
        self.averageGasPrice = averageGasPrice
        self.sumGasPrice = sumGasPrice
        self.transactions = transactions


class Validator(db.Model):
    id = db.Column(db.BIGINT, primary_key=True)
    address = db.Column(db.String(100))
    tokens = db.Column(db.String(100))
    moniker = db.Column(db.String(100))
    delegator_shares = db.Column(db.String(500))
    comission_rate = db.Column(db.String(500))
    website = db.Column(db.String(500))
    details = db.Column(db.String(500))

    def __init__(
            self,
            address: str,
            tokens: int,
            delegator_shares: float,
            moniker: str,
            comission_rate: float,
            website: str,
            details: str
    ):
        self.address = address
        self.tokens = tokens
        self.delegator_shares = delegator_shares
        self.moniker = moniker
        self.comission_rate = comission_rate
        self.website = website
        self.details = details


def validator_loader(v: dict) -> Validator:
    if 'website' in v['description']:
        website = v['description']['website']
    else:
        website = ""
    if 'details' in v['description']:
        details = v['description']['details']
    else:
        details = ""
    return Validator(
        address=v['operator_address'],
        tokens=v['tokens'],
        delegator_shares=float(v['delegator_shares']),
        moniker=v['description']['moniker'],
        comission_rate=v['commission']['commission_rates']['rate'],
        website=website,
        details=details
    )