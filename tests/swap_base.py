import os
import time
from functools import reduce

from mock import patch
from neocore.Cryptography.Crypto import Crypto
from neocore.Fixed8 import Fixed8

from nash.owner import TOKEN_OWNER1, TOKEN_OWNER2, TOKEN_OWNER3
from neo.Core.Block import Block, Header
from neo.Core.Blockchain import Blockchain
from neo.Core.TX.Transaction import Transaction
from neo.Core.TX.TransactionAttribute import (TransactionAttribute,
                                              TransactionAttributeUsage)
from neo.Core.Witness import Witness
from neo.Implementations.Blockchains.LevelDB.LevelDBBlockchain import \
    LevelDBBlockchain
from neo.Settings import settings
from tests.nex_test_base import NexFixtureTest


class TestSwapBase(NexFixtureTest):

    FIXTURE_REMOTE_LOC = 'https://s3.us-east-2.amazonaws.com/cityofzion/nex/vaultnetV3.tar.gz'
    FIXTURE_FILENAME = './fixtures/vaulnetV3.tar.gz'

    deployed_contract_hash = None
    unspent_gas = None
    unspent_neo = None

    swap_contract = None
    nex_contract = None


    INITIALIZED_SWAP_BASE = False

    @classmethod
    def leveldb_testpath(self):
        return os.path.join(settings.DATA_DIR_PATH, 'Chains/vaultnet')

    def setUp(self):
        super(TestSwapBase, self).setUp()

        if not TestSwapBase.INITIALIZED_SWAP_BASE:
            TestSwapBase.INITIALIZED_SWAP_BASE = True
            self.setup_swap_contracts()

    @classmethod
    def tearDownClass(cls):

        TestSwapBase.INITIALIZED_SWAP_BASE = False
        return super(TestSwapBase, cls).tearDownClass()

    def setup_swap_contracts(self):

        settings.log_smart_contract_events = False

        self.setup_deploy_nex_token()
        self.setup_deploy_swap_contracts()
        self.setup_approve_transfer_to_swap()

    def setup_deploy_nex_token(self):
        owner_wallet = self.GetOwner1()
        token_owner = self.GetTokenOwner()

        nex_contract_hash, block = self._deploy_compiled_contract_to_blockchain('%s/fixtures/NEX.avm' % settings.DATA_DIR_PATH, owner_wallet)
        TestSwapBase.nex_contract = nex_contract_hash
        
        tx, results = self.invoke_test(owner_wallet, 'initializeOwners', [], contract=nex_contract_hash.ToString())
        tx, block = self._invoke_tx_on_blockchain(tx, owner_wallet)

        tx, results = self.invoke_test(token_owner, 'ownerMint', ['owner1'], contract=nex_contract_hash.ToString())
        self.assertEqual(results[0].GetBoolean(), True)

        tx, block = self._invoke_tx_on_blockchain(tx, token_owner)

        # now send some NEX to wallet 2 and 3

    def setup_deploy_swap_contracts(self):

        owner_wallet = self.GetOwner1()

        swap_contract, block = self._deploy_contract_to_blockcahin('%s/NexSwap.py' % settings.DATA_DIR_PATH, owner_wallet)
        TestSwapBase.swap_contract = swap_contract

        # Initialize owners on swap contract
        tx, results = self.invoke_test(owner_wallet, 'initializeOwners', [], contract=swap_contract.ToString())
        self.assertTrue(results[0].GetBoolean())
        tx, block = self._invoke_tx_on_blockchain(tx, owner_wallet)

        # # Set contract to swap
        # print("CONTRACT: %s " % TestSwapBase.nex_contract.Data)
        # tx, results = self.invoke_test(owner_wallet, 'setSwapTokenContract', [TestSwapBase.nex_contract.Data], contract=swap_contract.ToString())
        # self.assertTrue(results[0].GetBoolean())
        # tx, block = self._invoke_tx_on_blockchain(tx, owner_wallet)

        token_owner = self.GetTokenOwner()
        token = self.nep5_token_from_contract(TestSwapBase.nex_contract)

        # send 100000 nex to owner1, owner2, owner3
        send_tx, fee, results = token.Transfer(token_owner, self.token_owner_addr(), self.owner1_addr(), Fixed8.FromDecimal(100000).value)
        tx, block = self._invoke_tx_on_blockchain(send_tx, token_owner)

        send_tx, fee, results = token.Transfer(token_owner, self.token_owner_addr(), self.owner2_addr(), Fixed8.FromDecimal(100000).value)
        tx, block = self._invoke_tx_on_blockchain(send_tx, token_owner)

        send_tx, fee, results = token.Transfer(token_owner, self.token_owner_addr(), self.owner3_addr(), Fixed8.FromDecimal(100000).value)
        tx, block = self._invoke_tx_on_blockchain(send_tx, token_owner)

        self.assertEqual(token.GetBalance(owner_wallet, self.owner1_addr()), 100000)
        self.assertEqual(token.GetBalance(owner_wallet, self.owner2_addr()), 100000)
        self.assertEqual(token.GetBalance(owner_wallet, self.owner3_addr()), 100000)

    def setup_approve_transfer_to_swap(self):

        user_wallet = self.GetTokenOwner()
        owner = self.GetOwner1()
        owner2 = self.GetOwner2()
        owner3 = self.GetOwner3()

        token = self.nep5_token_from_contract(TestSwapBase.nex_contract)

        # we need to apprvoe the swap contract to transfer from
        deposit_amount = Fixed8.FromDecimal(500000)

        approve_tx, fee, results = token.Approve(user_wallet, self.token_owner_addr(), TestSwapBase.swap_contract.Data, deposit_amount.value)
        tx, block = self._invoke_tx_on_blockchain(approve_tx, user_wallet)
        self.assertIsInstance(tx, Transaction)

        approve_amount = Fixed8.FromDecimal(50000).value

        # owner1 50k to swap
        a, f, r = token.Approve(owner, self.owner1_addr(), TestSwapBase.swap_contract.Data, approve_amount)
        self._invoke_tx_on_blockchain(a, owner)

        # owner2 50k to swap
        a, f, r = token.Approve(owner, self.owner2_addr(), TestSwapBase.swap_contract.Data, approve_amount)
        self._invoke_tx_on_blockchain(a, owner2)

        # owner3 50k to swap
        a, f, r = token.Approve(owner, self.owner3_addr(), TestSwapBase.swap_contract.Data, approve_amount)
        self._invoke_tx_on_blockchain(a, owner3)

        # just to make sure
        tx, fee, result = token.Allowance(owner, self.owner1_addr(), TestSwapBase.swap_contract.Data)
        self.assertEqual(result[0].GetBigInteger(), approve_amount)

