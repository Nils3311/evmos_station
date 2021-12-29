import datetime

from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy
db = SQLAlchemy()


class Transaction(db.Model):
    tx_id = db.Column(db.BIGINT, primary_key=True)
    gasPrice = db.Column(db.BIGINT)
    gas = db.Column(db.BIGINT)
    tx_type = db.Column(db.BIGINT)
    hash = db.Column(db.String(100))
    value = db.Column(db.NUMERIC(38, 0))
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
    tokens = db.Column(db.NUMERIC(38, 0))
    moniker = db.Column(db.String(100))
    delegator_shares = db.Column(db.NUMERIC(38, 0))
    self_share = db.Column(db.FLOAT)
    power_share = db.Column(db.FLOAT)
    comission_rate = db.Column(db.FLOAT)
    website = db.Column(db.String(500))
    details = db.Column(db.String(500))
    jailed = db.Column(db.Boolean)
    status = db.Column(db.String(100))

    def __init__(
            self,
            address: str,
            tokens: int,
            delegator_shares: float,
            moniker: str,
            self_share: float,
            comission_rate: float,
            website: str,
            details: str,
            jailed: str,
            status: str
    ):
        self.address = address
        self.tokens = tokens
        self.delegator_shares = delegator_shares
        self.moniker = moniker
        self.self_share = self_share
        self.comission_rate = comission_rate
        self.website = website
        self.details = details
        self.status = status
        self.jailed = jailed


def validator_loader(v: dict) -> Validator:
    if 'website' in v['description']:
        website = v['description']['website']
    else:
        website = ""
    if 'details' in v['description']:
        details = v['description']['details']
    else:
        details = ""
    tokens = int(v['tokens'])
    delegator_shares = round(float(v['delegator_shares']), 2)
    return Validator(
        address=v['operator_address'],
        tokens=tokens,
        delegator_shares=delegator_shares,
        self_share=tokens / delegator_shares,
        moniker=v['description']['moniker'],
        comission_rate=round(float(v['commission']['commission_rates']['rate']), 4),
        website=website,
        details=details,
        jailed=v['jailed'],
        status=v['status']
    )


class Faucet(db.Model):
    number = db.Column(db.BIGINT, primary_key=True)
    timestamp = db.Column(db.BIGINT)
    address = db.Column(db.String(100))

    def __init__(self, timestamp, address):
        self.timestamp = timestamp
        self.address = address


class Governance(db.Model):
    id = db.Column(db.BIGINT, primary_key=True)
    proposal_id = db.Column(db.BIGINT)
    proposal_type = db.Column(db.String(200))
    title = db.Column(db.String(400))
    description = db.Column(db.String(5000))
    status = db.Column(db.String(200))
    result_yes = db.Column(db.NUMERIC(38, 0))
    result_no = db.Column(db.NUMERIC(38, 0))
    result_abstain = db.Column(db.NUMERIC(38, 0))
    result_no_with_veto = db.Column(db.NUMERIC(38, 0))
    deposit_amount = db.Column(db.NUMERIC(38, 0))
    voting_start = db.Column(db.BIGINT)
    voting_end = db.Column(db.BIGINT)
    submit_start = db.Column(db.BIGINT)
    deposit_end = db.Column(db.BIGINT)

    def __init__(
            self,
            proposal_id: int,
            proposal_type: str,
            title: str,
            description: str,
            status: str,
            result_yes: int,
            result_no: int,
            result_abstain: int,
            result_no_with_veto: int,
            voting_start: int,
            voting_end: int,
            submit_start: int,
            deposit_end: int
    ):
        self.proposal_id = proposal_id
        self.proposal_type = proposal_type
        self.title = title
        self.description = description
        self.status = status
        self.result_yes = result_yes
        self.result_no = result_no
        self.result_abstain = result_abstain
        self.result_no_with_veto = result_no_with_veto
        self.voting_start = voting_start
        self.voting_end = voting_end
        self.submit_start = submit_start
        self.deposit_end = deposit_end


def governance_loader(v: dict) -> Governance:
    return Governance(
        proposal_id=v['proposal_id'],
        proposal_type=v['content']['@type'],
        title=v['content']['title'],
        description=v['content']['description'],
        status=v['status'],
        result_yes=v['final_tally_result']['yes'],
        result_no=v['final_tally_result']['no'],
        result_abstain=v['final_tally_result']['abstain'],
        result_no_with_veto=v['final_tally_result']['no_with_veto'],
        voting_start=datetime.datetime.strptime(v['voting_start_time'].split(".")[0], "%Y-%m-%dT%H:%M:%S").timestamp(),
        voting_end=datetime.datetime.strptime(v['voting_end_time'].split(".")[0], "%Y-%m-%dT%H:%M:%S").timestamp(),
        submit_start=datetime.datetime.strptime(v['submit_time'].split(".")[0], "%Y-%m-%dT%H:%M:%S").timestamp(),
        deposit_end=datetime.datetime.strptime(v['deposit_end_time'].split(".")[0], "%Y-%m-%dT%H:%M:%S").timestamp()
    )
