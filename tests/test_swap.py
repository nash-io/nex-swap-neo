import os
import time

from mock import patch
from neocore.Fixed8 import Fixed8

from neo.Core.Block import Block, Header
from neo.Core.Blockchain import Blockchain
from neo.Core.TX.Transaction import Transaction
from neo.Implementations.Blockchains.LevelDB.LevelDBBlockchain import \
    LevelDBBlockchain
from neo.Settings import settings
from tests.nex_test_base import NexFixtureTest
from tests.swap_base import TestSwapBase


class TestSwap(TestSwapBase):

    def test_a_swap_from_neo(self):

        user_wallet = self.GetTokenOwner()
        token = self.nep5_token_from_contract(TestSwapBase.nex_contract)

        current_balance_user = int(token.GetBalance(user_wallet, self.token_owner_addr()))
        current_balance_contract = int(token.GetBalance(user_wallet, TestSwapBase.swap_contract))

        amountToSwap = 1000
        eth_addr = bytes.fromhex('7FAB4CB3D917719284F9E715A9c6B6FA1fBA217f')
        swap_args = [self.token_owner_addr(), eth_addr, Fixed8.FromDecimal(amountToSwap).value]

        tx, results = self.invoke_test(user_wallet, 'swapToEth', swap_args, contract=TestSwapBase.swap_contract.ToString())
        self.assertEqual(results[0].GetBoolean(), True)

        self.dispatched_events = []
        tx, block = self._invoke_tx_on_blockchain(tx, user_wallet)

        # now get the last event dispatched
        swap_event = self.dispatched_events[-1]
        self.assertEqual(swap_event.notify_type, b'onSwapToEth')
        event_results = swap_event.event_payload.Value
        self.assertEqual(len(event_results), 5)
        amount = event_results[3].Value
        ethAddr = event_results[2].Value
        addr = event_results[1].Value
        swapId = event_results[4].Value
        self.assertEqual(Fixed8.FromDecimal(amountToSwap).value, int.from_bytes(amount, 'little'))
        self.assertEqual(addr, self.token_owner_sh())
        self.assertEqual(ethAddr, eth_addr)

        new_balance_user = int(token.GetBalance(user_wallet, self.token_owner_addr()))
        new_balance_contract = int(token.GetBalance(user_wallet, TestSwapBase.swap_contract))

        self.assertEqual(new_balance_contract, current_balance_contract + amountToSwap)
        self.assertEqual(new_balance_user, current_balance_user - amountToSwap)

        tx, results = self.invoke_test(user_wallet, 'totalSwapped', [], contract=TestSwapBase.swap_contract.ToString())
        amount = results[0].GetBigInteger()
        self.assertEqual(Fixed8.FromDecimal(new_balance_contract).value, amount)

        # invalid eth address
        invalid_eth_addr = bytes.fromhex('7FAB4CB3D917719284F9E715A9c6B6FA1fBA2a')
        swap_args = [self.token_owner_addr(), invalid_eth_addr, Fixed8.FromDecimal(amountToSwap).value]

        tx, results = self.invoke_test(user_wallet, 'swapToEth', swap_args, contract=TestSwapBase.swap_contract.ToString())
        self.assertEqual(len(results), 0)

        # Test min swap amount
        amountToSwap = 499.99999
        swap_args = [self.token_owner_addr(), eth_addr, Fixed8.FromDecimal(amountToSwap).value]

        tx, results = self.invoke_test(user_wallet, 'swapToEth', swap_args, contract=TestSwapBase.swap_contract.ToString())
        self.assertEqual(len(results), 0)


    def test_b_swap_from_eth(self):

        user_wallet = self.GetTokenOwner()
        token = self.nep5_token_from_contract(TestSwapBase.nex_contract)
        current_balance_user = int(token.GetBalance(user_wallet, self.token_owner_addr()))

        amountToSwap = 1000
        eth_addr = bytes.fromhex('7FAB4CB3D917719284F9E715A9c6B6FA1fBA217f')
        swap_id = 'a4272b7709b4e2dd0a208c020f6e0418b8a32f95c1c564d0c3b158ef47d496217FAB4CB3D917719284F9E715A9c6B6FA1fBA217f'
        swap_args = [self.token_owner_addr(), eth_addr, Fixed8.FromDecimal(amountToSwap).value, swap_id]

        # should fail, only owner can swap from eth
        tx, results = self.invoke_test(user_wallet, 'swapFromEth', swap_args, contract=TestSwapBase.swap_contract.ToString())
        self.assertFalse(results[0].GetBoolean())

        owner_wallet = self.GetOwner1()

        # cant swap back more than has been swapped
        swap_args = [self.token_owner_addr(), eth_addr, Fixed8.FromDecimal(amountToSwap+1).value, swap_id]
        tx, results = self.invoke_test(owner_wallet, 'swapFromEth', swap_args, contract=TestSwapBase.swap_contract.ToString())
        self.assertEqual(len(results), 0)

        # should be ok
        swap_args = [self.token_owner_addr(), eth_addr, Fixed8.FromDecimal(amountToSwap).value, swap_id]
        tx, results = self.invoke_test(owner_wallet, 'swapFromEth', swap_args, contract=TestSwapBase.swap_contract.ToString())
        self.assertEqual(results[0].GetBoolean(), True)


        self.dispatched_events = []
        tx, block = self._invoke_tx_on_blockchain(tx, owner_wallet)

        # now get the last event dispatched
        swap_event = self.dispatched_events[-1]
        self.assertEqual(swap_event.notify_type, b'onSwapFromEth')
        event_results = swap_event.event_payload.Value
        self.assertEqual(len(event_results), 5)
        amount = event_results[3].Value
        ethAddr = event_results[2].Value
        addr = event_results[1].Value
        swapid = event_results[4].Value
        self.assertEqual(Fixed8.FromDecimal(amountToSwap).value, int.from_bytes(amount, 'little'))
        self.assertEqual(addr, self.token_owner_sh())
        self.assertEqual(ethAddr, eth_addr)
        self.assertEqual(swap_id, swapid.decode('utf-8'))
        tx, results = self.invoke_test(user_wallet, 'totalSwapped', [], contract=TestSwapBase.swap_contract.ToString())

        self.assertEqual(results[0].GetBigInteger(), 0)

        new_balance_user = int(token.GetBalance(user_wallet, self.token_owner_addr()))
        self.assertEqual(new_balance_user, current_balance_user + amountToSwap)

        # Now try with same swap ID, should fail
        swap_args = [self.token_owner_addr(), eth_addr, Fixed8.FromDecimal(amountToSwap).value, swap_id]
        tx, results = self.invoke_test(owner_wallet, 'swapFromEth', swap_args, contract=TestSwapBase.swap_contract.ToString())
        self.assertEqual(len(results), 0)
