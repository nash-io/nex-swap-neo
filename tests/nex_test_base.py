import datetime
import os
import shutil
import tarfile
from uuid import uuid4

import logzero
import requests
from boa.compiler import Compiler
from logzero import logger
from neocore.KeyPair import KeyPair
from neocore.UInt160 import UInt160

from neo.Core.Block import Block
from neo.Core.Blockchain import Blockchain
from neo.Core.TX.MinerTransaction import MinerTransaction
from neo.Core.TX.Transaction import Transaction
from neo.Core.TX.TransactionAttribute import (TransactionAttribute,
                                              TransactionAttributeUsage)
from neo.Core.Witness import Witness
from neo.EventHub import events
from neo.Implementations.Blockchains.LevelDB.LevelDBBlockchain import \
    LevelDBBlockchain
from neo.Implementations.Wallets.peewee.UserWallet import UserWallet
from neo.Network.NodeLeader import NodeLeader
from neo.Prompt.Commands.BuildNRun import generate_deploy_script
from neo.Prompt.Commands.Invoke import TestInvokeContract, test_invoke
from neo.Prompt.Commands.LoadSmartContract import LoadContract
from neo.Settings import settings
from neo.SmartContract.ContractParameterContext import \
    ContractParametersContext
from neo.SmartContract.SmartContractEvent import (NotifyEvent,
                                                  SmartContractEvent)
from neo.Utils.BlockchainFixtureTestCase import BlockchainFixtureTestCase
from neo.Wallets.NEP5Token import NEP5Token
from neo.Wallets.utils import to_aes_key

settings.USE_DEBUG_STORAGE = True
settings.DEBUG_STORAGE_PATH = './fixtures/debugstorage'
settings.LOG_SMART_CONTRACT_EVENTS = True
settings.DATA_DIR_PATH = os.getcwd()

class NexFixtureTest(BlockchainFixtureTestCase):

    FIXTURE_REMOTE_LOC = 'https://s3.us-east-2.amazonaws.com/cityofzion/fixtures/empty_fixture.tar.gz'
    FIXTURE_FILENAME = './fixtures/empty_fixture.tar.gz'

    dirname = None

    dispatched_events = []
    dispatched_logs = []
    failure_events = []

    deployed_contract = None

    @classmethod
    def leveldb_testpath(self):
        return os.path.join(settings.DATA_DIR_PATH, 'fixtures/test_chain')

    def on_notif(self, evt):
        ntype = ''
        if isinstance(evt, NotifyEvent):
            ntype = evt.Type
            if ntype is None:
                ntype = 'print'

        logger.info('[notification "%s"]: %s ' % (ntype.upper(), evt.event_payload.ToJson()))
        self.dispatched_events.append(evt)

    def on_fail(self, evt):
        self.failure_events.append(evt)

    def on_log(self, evt):
        if isinstance(evt.event_payload.Value, dict):
            try:
                logger.info('[log]: %s ' % json.dumps(evt.event_payload.Value, indent=4))
            except Exception as e:
                print("Could not parse json: %s " % e)
                logger.info('[log]: %s ' % evt.event_payload.ToJson())
        else:
            logger.info('[log]: %s ' % evt.event_payload.ToJson())
        self.dispatched_logs.append(evt)

    def setUp(self):
        events.on(SmartContractEvent.RUNTIME_NOTIFY, self.on_notif)
        events.on(SmartContractEvent.RUNTIME_LOG, self.on_log)
        events.on(SmartContractEvent.EXECUTION_FAIL, self.on_fail)

    def tearDown(self):
        events.off(SmartContractEvent.RUNTIME_NOTIFY, self.on_notif)
        events.off(SmartContractEvent.RUNTIME_LOG, self.on_log)
        events.off(SmartContractEvent.EXECUTION_FAIL, self.on_fail)

    @classmethod
    def wallet_pw(cls):
        return 'nexpassword'

    @classmethod
    def token_owner_wallet(cls):
        return 'test_owner1'

    @classmethod
    def wtest1_wallet(cls):
        return 'vtest1'

    @classmethod
    def wtest2_wallet(cls):
        return 'vtest2'

    @classmethod
    def wtest3_wallet(cls):
        return 'vtest3'

    @classmethod
    def wtest4_wallet(cls):
        return 'vtest4'

    @classmethod
    def owner1_wallet(cls):
        return 'vowner1'

    @classmethod
    def owner2_wallet(cls):
        return 'vowner2'

    @classmethod
    def owner3_wallet(cls):
        return 'vowner3'

    @classmethod
    def owner4_wallet(cls):
        return 'vowner4'

    @classmethod
    def owner5_wallet(cls):
        return 'vowner5'

    @classmethod
    def agent_wallet(cls):
        return 'vault_agent'

    @classmethod
    def monitor_wallet(cls):
        return 'vault_monitor'

    @classmethod
    def token_owner_addr(cls):
        return 'AWeZnH735EavQJKbJPC5F8fxutBnJFhukW'

    @classmethod
    def token_owner_sh(cls):
        return b'\xa3(\x0f\xb5\x00\x93\x10\xad\xe9\xb3<\x07\xe6\xa6|U2\xe2\xfc\x10'

    @classmethod
    def owner1_addr(cls):
        return 'ASsxu2siiFNP4xAfqXx7LD9vUW7ZMSyyKJ'

    @classmethod
    def owner1_sh(cls):
        return b'y\xd0C*\xd9\x00\xb7#\xc3.\x1c\x17\xb5.\xeeX\x1el\xbfW'

    @classmethod
    def owner2_addr(cls):
        return 'AUbfVhGwvSoZdTTu2PRz4ki9S2p7aDZtiV'

    @classmethod
    def owner2_sh(cls):
        return b'\x8c\xabT\xefe\x9b\x1d\x02n\xc1\x9f\x0cC\xb86}\x0b7\xa2\x9a'

    @classmethod
    def owner3_addr(cls):
        return 'AWncfPJHoxcto1GkjAbZbgGtxfYbr8TXuA'

    @classmethod
    def owner3_sh(cls):
        return b'\xa4\xad\xcbK\x11K=\x00H\xd9o\xb9w\xe9\xd1\x85\x83\xf35\x87'

    @classmethod
    def owner4_addr(cls):
        return 'ARu3b1gHQdHcEFYQQG37j9JRThGJ66pYZR'

    @classmethod
    def owner4_sh(cls):
        return b'o\x0cw\x8c\x08{\x10H\xe4 \x80(\xfa\xf7Uz\x0cY\xf2\xa6'

    @classmethod
    def owner5_addr(cls):
        return 'AP9GKDjYZs5WYVo3uqtUztdkafm65JVssL'

    @classmethod
    def owner5_sh(cls):
        return b'P\xd4\x89\xa4,],\xe7\x88\xbaFd\xa5\xc0!w\xd4\x15\xcfx'

    @classmethod
    def wtest1_addr(cls):
        return 'ALeWWznK4c5zBk8MGYpazZ3vKxD5asxwte'

    @classmethod
    def wtest1_sh(cls):
        return b'5t\x14M\x85%\r\xc2rF\x0f\xf5Wx\xae\xc4T\x06\xb8g'

    @classmethod
    def wtest2_addr(cls):
        return 'ASk62tjEpfhRJw7VCDDVQAyQgY5kbCXTA6'

    @classmethod
    def wtest2_sh(cls):
        return b'xR\xe4\x1f;bSI\x80\x04<\x06(\xd9\xf7w\xe7\xd8\x8c\x98'

    @classmethod
    def wtest3_addr(cls):
        return 'AdBTH9bFUjzFoXwFMxALeyEMPAK8j3ae17'

    @classmethod
    def wtest3_sh(cls):
        return b'\xea\xd0Hx\x19=\x9f\x13M\xd2\xf4\x82=\xd2\xe0\xb82\x90\xe6)'

    @classmethod
    def wtest4_addr(cls):
        return 'AQdPQPhDHnF5teMXWoq9GsH2ioPPHNdJ1P'

    @classmethod
    def wtest4_sh(cls):
        return b'a\x1e:e\xb2\xf8\xae\xb5b\xf6\x9b\x83\xd3\xd1\xd9\xe9&\x9b\xe0\xfe'

    @classmethod
    def nex_token_hash(cls):
        return UInt160.ParseString('5cfbca68b34f07b14429eb2e735ad4dfd8234d6a')

    @classmethod
    def nex_nep5_token(cls):
        tokenContract = Blockchain.Default().GetContract(NexFixtureTest.nex_token_hash().ToBytes())
        nep5 = NEP5Token(script=tokenContract.Code.Script)
        nep5.Query()
        return nep5

    @classmethod
    def nep5_token_from_contract(cls, contract: UInt160):
        tokenContract = Blockchain.Default().GetContract(contract.ToBytes())
        nep5 = NEP5Token(script=tokenContract.Code.Script)
        nep5.Query()
        return nep5

    @classmethod
    def get_wallet(cls, wallet_name):
        wallet = UserWallet.Open('./tmp/%s' % wallet_name, to_aes_key(cls.wallet_pw()))
        return wallet

    @classmethod
    def get_wallet_hash(cls, wallet) -> UInt160:
        return wallet.GetDefaultContract().ScriptHash

    @classmethod
    def get_wallet_keypair(cls, wallet) -> KeyPair:
        return wallet.GetKeyByScriptHash(cls.get_wallet_hash(wallet))

    @classmethod
    def get_hash_and_keypair(cls, wallet) -> (UInt160, KeyPair):
        return cls.get_wallet_hash(wallet), cls.get_wallet_keypair(wallet)

    wallet1 = None
    wallet2 = None
    wallet3 = None
    wallet4 = None
    tokenOwner1 = None
    owner1 = None
    owner2 = None
    owner3 = None
    owner4 = None
    owner5 = None

    agent = None
    monitor = None

    @classmethod
    def GetWallet1(cls, recreate=False):
        if not cls.wallet1 or recreate:
            cls.wallet1 = NexFixtureTest.get_wallet(NexFixtureTest.wtest1_wallet())
        return cls.wallet1

    @classmethod
    def GetWallet2(cls):
        if not cls.wallet2:
            cls.wallet2 = NexFixtureTest.get_wallet(NexFixtureTest.wtest2_wallet())
        return cls.wallet2

    @classmethod
    def GetWallet3(cls):
        if not cls.wallet3:
            cls.wallet3 = NexFixtureTest.get_wallet(NexFixtureTest.wtest3_wallet())
        return cls.wallet3

    @classmethod
    def GetWallet4(cls):
        if not cls.wallet4:
            cls.wallet4 = NexFixtureTest.get_wallet(NexFixtureTest.wtest4_wallet())
        return cls.wallet4

    def GetTokenOwner(cls, recreate=False):
        if not cls.tokenOwner1 or recreate:
            cls.tokenOwner1 = NexFixtureTest.get_wallet(NexFixtureTest.token_owner_wallet())
        return cls.tokenOwner1

    @classmethod
    def GetOwner1(cls, recreate=False):
        if not cls.owner1 or recreate:
            cls.owner1 = NexFixtureTest.get_wallet(NexFixtureTest.owner1_wallet())
        return cls.owner1

    @classmethod
    def GetOwner2(cls):
        if not cls.owner2:
            cls.owner2 = NexFixtureTest.get_wallet(NexFixtureTest.owner2_wallet())
        return cls.owner2

    @classmethod
    def GetOwner3(cls):
        if not cls.owner3:
            cls.owner3 = NexFixtureTest.get_wallet(NexFixtureTest.owner3_wallet())
        return cls.owner3

    @classmethod
    def GetOwner4(cls):
        if not cls.owner4:
            cls.owner4 = NexFixtureTest.get_wallet(NexFixtureTest.owner4_wallet())
        return cls.owner4

    @classmethod
    def GetOwner5(cls):
        if not cls.owner5:
            cls.owner5 = NexFixtureTest.get_wallet(NexFixtureTest.owner5_wallet())
        return cls.owner5

    @classmethod
    def GetAgentWallet(cls, recreate=False):
        if not cls.agent or recreate:
            cls.agent = NexFixtureTest.get_wallet(NexFixtureTest.agent_wallet())
        return cls.agent

    @classmethod
    def GetMonitorWallet(cls, recreate=False):
        if not cls.monitor or recreate:
            cls.monitor = NexFixtureTest.get_wallet(NexFixtureTest.monitor_wallet())
        return cls.monitor

    @classmethod
    def setUpClass(cls):

        try:
            Blockchain.DeregisterBlockchain()

            super(BlockchainFixtureTestCase, cls).setUpClass()

            if not os.path.exists(cls.FIXTURE_FILENAME):
                logzero.logger.info(
                    "downloading fixture block database from %s. this may take a while" % cls.FIXTURE_REMOTE_LOC)

                response = requests.get(cls.FIXTURE_REMOTE_LOC, stream=True)

                response.raise_for_status()
                os.makedirs(os.path.dirname(cls.FIXTURE_FILENAME), exist_ok=True)
                with open(cls.FIXTURE_FILENAME, 'wb+') as handle:
                    for block in response.iter_content(1024):
                        handle.write(block)

            try:
                tar = tarfile.open(cls.FIXTURE_FILENAME)
                tar.extractall(path=settings.DATA_DIR_PATH)
                tar.close()
            except Exception as e:
                raise Exception("Could not extract tar file - %s. You may want need to remove the fixtures file %s manually to fix this." % (e, cls.FIXTURE_FILENAME))

            if not os.path.exists(cls.leveldb_testpath()):
                raise Exception("Error downloading fixtures at %s" % cls.leveldb_testpath())

            settings.setup_unittest_net()

            cls._blockchain = LevelDBBlockchain(path=cls.leveldb_testpath(), skip_version_check=True)
            Blockchain.RegisterBlockchain(cls._blockchain)

            shutil.copyfile('./fixtures/%s' % cls.wtest1_wallet(), './tmp/%s' % cls.wtest1_wallet())
            shutil.copyfile('./fixtures/%s' % cls.wtest2_wallet(), './tmp/%s' % cls.wtest2_wallet())
            shutil.copyfile('./fixtures/%s' % cls.wtest3_wallet(), './tmp/%s' % cls.wtest3_wallet())
            shutil.copyfile('./fixtures/%s' % cls.wtest4_wallet(), './tmp/%s' % cls.wtest4_wallet())
            shutil.copyfile('./fixtures/%s' % cls.owner1_wallet(), './tmp/%s' % cls.owner1_wallet())
            shutil.copyfile('./fixtures/%s' % cls.owner2_wallet(), './tmp/%s' % cls.owner2_wallet())
            shutil.copyfile('./fixtures/%s' % cls.owner3_wallet(), './tmp/%s' % cls.owner3_wallet())
            shutil.copyfile('./fixtures/%s' % cls.owner4_wallet(), './tmp/%s' % cls.owner4_wallet())
            shutil.copyfile('./fixtures/%s' % cls.owner5_wallet(), './tmp/%s' % cls.owner5_wallet())
            shutil.copyfile('./fixtures/%s' % cls.token_owner_wallet(), './tmp/%s' % cls.token_owner_wallet())
            shutil.copyfile('./fixtures/%s' % cls.agent_wallet(), './tmp/%s' % cls.agent_wallet())
            shutil.copyfile('./fixtures/%s' % cls.monitor_wallet(), './tmp/%s' % cls.monitor_wallet())

            NodeLeader.Instance().MemPool = {}

        except Exception as e:
            print("Could not setup NexSimpleTset: %s " % e)

    @classmethod
    def tearDownClass(cls):

        # tear down Blockchain DB
        Blockchain.Default().DeregisterBlockchain()
        if cls._blockchain is not None:
            cls._blockchain.Dispose()

        shutil.rmtree(cls.leveldb_testpath())

        NodeLeader.Instance().MemPool = {}

        if cls.wallet1:
            cls.wallet1.Close()
        if cls.wallet2:
            cls.wallet2.Close()
        if cls.wallet3:
            cls.wallet3.Close()
        if cls.wallet4:
            cls.wallet4.Close()
        if cls.owner1:
            cls.owner1.Close()
        if cls.owner2:
            cls.owner2.Close()
        if cls.owner3:
            cls.owner3.Close()
        if cls.owner4:
            cls.owner4.Close()
        if cls.owner5:
            cls.owner5.Close()
        if cls.agent:
            cls.agent.Close()
        if cls.monitor:
            cls.monitor.Close()
        if cls.tokenOwner1:
            cls.tokenOwner1.Close()
        try:
            os.remove('./tmp/%s' % cls.wtest1_wallet())
            os.remove('./tmp/%s' % cls.wtest2_wallet())
            os.remove('./tmp/%s' % cls.wtest3_wallet())
            os.remove('./tmp/%s' % cls.wtest4_wallet())
            os.remove('./tmp/%s' % cls.owner1_wallet())
            os.remove('./tmp/%s' % cls.owner2_wallet())
            os.remove('./tmp/%s' % cls.owner3_wallet())
            os.remove('./tmp/%s' % cls.owner4_wallet())
            os.remove('./tmp/%s' % cls.owner5_wallet())
            os.remove('./tmp/%s' % cls.token_owner_wallet())
            os.remove('./tmp/%s' % cls.agent_wallet())
            os.remove('./tmp/%s' % cls.monitor_wallet())

        except Exception as e:
            print("couldn't remove wallets %s " % e)

    def _deploy_contract_to_blockcahin(self, contract_path, wallet) -> (UInt160, Block):

        Compiler.instance().load_and_save(contract_path)

        compiled_contract_path = contract_path.replace('.py', '.avm')

        return self._deploy_compiled_contract_to_blockchain(compiled_contract_path, wallet)

    def _deploy_compiled_contract_to_blockchain(self, compiled_contract_path, wallet) -> (UInt160, Block):

        function_code = LoadContract([compiled_contract_path, '0710', '05', 'True', 'True', 'False'])

        contract_script = generate_deploy_script(function_code.Script, 'Test', '1', 'Test', 'Email', 'Test',
                                                 function_code.ContractProperties, function_code.ReturnTypeBigInteger,
                                                 function_code.ParameterList)

        tx, fee, results, num_ops = test_invoke(contract_script, wallet, [])
        wallet_tx = wallet.MakeTransaction(tx)
        context = ContractParametersContext(wallet_tx)
        wallet.Sign(context)
        wallet_tx.scripts = context.GetScripts()

        if NodeLeader.Instance().AddTransaction(wallet_tx):

            block = self._create_block_with_tx([wallet_tx])

            NexFixtureTest.deployed_contract = function_code.ScriptHash()

            return function_code.ScriptHash(), block

    def _invoke_tx_on_blockchain(self, transaction, wallet, make_tx=True, sync_wallet=True, fee=None, timestamp=None, sign=True, skip_verify=False) -> (Transaction, Block):
        if make_tx:
            if fee:
                transaction = wallet.MakeTransaction(transaction, fee=fee)
            else:
                transaction = wallet.MakeTransaction(transaction)

            transaction.Attributes.append(
                TransactionAttribute(usage=TransactionAttributeUsage.Script, data=wallet.GetDefaultContract().ScriptHash.Data)
            )
            transaction.Attributes.append(
                TransactionAttribute(usage=TransactionAttributeUsage.Remark1, data=int(datetime.datetime.now().timestamp()).to_bytes(8, 'little'))
            )

        if sign:
            context = ContractParametersContext(transaction)
            wallet.Sign(context)
            transaction.scripts = context.GetScripts()

        if skip_verify or NodeLeader.Instance().AddTransaction(transaction):
            block = self._create_block_with_tx([transaction], timestamp=timestamp)

            if sync_wallet:
                wallet.ProcessNewBlock(block)

            return transaction, block

        return False, False

    def _create_block_with_tx(self, tx_list, timestamp=None) -> Block:

        if timestamp is None:
            timestamp = int(datetime.datetime.utcnow().timestamp())

        try:
            m = MinerTransaction()
            m.Nonce = 12345678

            tx_list.insert(0, m)
            cdata = UInt160(data=bytearray(20))

            prevhash = Blockchain.Default().GetBlockByHeight(Blockchain.Default().Height).Hash
            witness = Witness(invocation_script=bytearray([1]), verification_script=bytearray([2]))

            block = Block(prevHash=prevhash,
                          timestamp=timestamp,
                          index=Blockchain.Default().Height+1,
                          consensusData=1234, script=witness,
                          nextConsensus=cdata, transactions=tx_list, build_root=True)

            Blockchain.Default().AddHeaders([block.Header])

            Blockchain.Default().AddBlockDirectly(block, do_persist_complete=True)

            return block
        except Exception as e:
            print("Could not create block!! %s " % e)
        return False

    def _sync_test_wallet(self, wallet):

        current_height = wallet.WalletHeight + 1
        blockchain_height = Blockchain.Default().Height + 1

        while current_height < blockchain_height:
            block = Blockchain.Default().GetBlockByHeight(current_height)
            wallet.ProcessNewBlock(block)
            current_height += 1

        return True

    def initialize_owners(self):

        # initialize owners
        owner_wallet = self.GetOwner1()

        tx, results = self.invoke_test(owner_wallet, 'initializeOwners')

        self.assertTrue(results[0].GetBoolean())
        self._invoke_tx_on_blockchain(tx, owner_wallet)

        # add matching engine pubkey
        me_pubkey = bytearray.fromhex(owner_wallet.PubKeys()[0]['Public Key'])
        whitelist_tx, results = self.invoke_test(owner_wallet, 'addMatchingEnginePubkey', [me_pubkey])

        # send to blockchain
        tx, block = self._invoke_tx_on_blockchain(whitelist_tx, owner_wallet)
        self.assertIsInstance(tx, Transaction)

    def setup_kyc_admin(self):

        owner_wallet = self.GetOwner1()

        tx, results = self.invoke_test(owner_wallet, 'addWhitelistAdmin', [self.owner1_sh()])

        self.assertTrue(results[0].GetBoolean())
        # add some unique data to make sure this goes through
        tx.Attributes = [TransactionAttribute(TransactionAttributeUsage.Remark2, data=str(uuid4()))]
        tx, block = self._invoke_tx_on_blockchain(tx, owner_wallet, make_tx=True)
        self.assertIsInstance(tx, Transaction)
        self.assertEqual(self.dispatched_events[-1].Type, 'OnAddedWhitelistAdmin')

    def whitelist_token(self):
        owner_wallet = self.GetOwner1()
        tx, results = self.invoke_test(owner_wallet, 'addToAssetWhitelist', [self.nex_token_hash().Data])
        self.assertTrue(results[0].GetBoolean())
        tx, block = self._invoke_tx_on_blockchain(tx, owner_wallet, make_tx=True)
        self.assertIsInstance(tx, Transaction)

    def invoke_test(self, wallet, method_name, params=[], extra=None, contract=None, owners=None, from_address=None) -> (Transaction, list):

        if contract is None:
            contract = NexFixtureTest.deployed_contract.ToString()

        tx, fee, results, numops = TestInvokeContract(wallet,
                                                      [contract,
                                                       method_name, params, extra], owners=owners, from_addr=from_address)

        return tx, results
