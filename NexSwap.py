"""
NEX Swap to ETH contract
===================================

Author: Thomas Saunders
Email: tom@nash.io

Date: Aug 28, 2020

"""
from nash.owner import *
from boa.interop.Neo.Runtime import GetTrigger, CheckWitness
from boa.interop.System.ExecutionEngine import GetExecutingScriptHash,GetScriptContainer
from boa.interop.Neo.TriggerType import Application, Verification
from boa.interop.Neo.Storage import *
from boa.interop.Neo.Action import RegisterAction
from boa.interop.Neo.App import DynamicAppCall
from boa.interop.Neo.Transaction import *

ctx = GetContext()

OnSwapToEth = RegisterAction("onSwapToEth", "addr", "ethAddr", "amount")
OnSwapFromEth = RegisterAction("onSwapFromEth", "addr", "ethAddr", "amount")

SWAP_CONTRACT_KEY= 'swapContract'


def Main(operation, args):
    """

    :param operation: str The name of the operation to perform
    :param args: list A list of arguments along with the operation
    :return:
        bytearray: The result of the operation
    """

    trigger = GetTrigger()

    # This is used in the Verification portion of the contract
    # To determine whether a transfer of system assets ( NEO/Gas) involving
    # This contract's address can proceed
    if trigger == Verification():

        return False

    elif trigger == Application():

        if operation == 'swapToEth':
            if len(args) == 3:
                return swapToEth(args)
            raise Exception("Invalid argument length")

        elif operation == 'swapFromEth':
            if len(args) == 3:
                return swapFromEth(args)
            raise Exception("Invalid argument length")

        elif operation == 'totalSwapped':
            return getTotalSwapped()

        # owner / admin methods
        elif operation == 'setSwapTokenContract':
            return setSwapContract(args)

        elif operation == 'initializeOwners':
            return initialize_owners(ctx)

        elif operation == 'getOwners':
            return get_owners(ctx)

        elif operation == 'checkOwners':
            return check_owners(ctx, 3)

        elif operation == 'switchOwner':
            return switch_owner(ctx, args)

        raise Exception("Unknown operation")

    return False


def swapToEth(args):
    addr = args[0]
    ethAddr = args[1]
    amount = args[2]
    
    validateEthAddr(ethAddr)
    validateNeoAddr(addr)

    tx = GetScriptContainer()
    txHash = tx.Hash

    if not CheckWitness(addr):
        raise Exception("Must be signed by swapper addr")

    if amount <= 0:
        raise Exception("Invalid amount")

    swapId = concat(txHash, addr)

    if Get(ctx, swapId) > 0:
        raise Exception("Already swap for this transaction and address")

    args = [addr, GetExecutingScriptHash(), amount]

    transferOfTokens = DynamicAppCall(getSwapContract(), 'transferFrom', args)

    if transferOfTokens:
        Put(ctx, swapId, 1)
        OnSwapToEth(addr, ethAddr, amount)
        return True

    raise Exception("Could not transfer tokens to swap contract")



def swapFromEth(args):
    """
    Only admin may execute a swap from eth
    """
    if check_owners(ctx, 1):
        addr = args[0]
        ethAddr = args[1]
        amount = args[2]

        validateEthAddr(ethAddr)
        validateNeoAddr(addr)

        totalAvailable = getTotalSwapped()
        if totalAvailable < amount:
            raise Exception("Can not swap back from eth tokens that were never swapped")

        ## transfer back to user
        args = [GetExecutingScriptHash(), addr, amount]

        transferOfTokens = DynamicAppCall(getSwapContract(), 'transfer', args)
        if transferOfTokens:
            OnSwapFromEth(addr,ethAddr,amount)
            return True
    return False


def getTotalSwapped():
    tokenContract = getSwapContract()
    contractAddress = GetExecutingScriptHash()
    args = [contractAddress]
    balance = DynamicAppCall(tokenContract,'balanceOf',args)

    return balance

def setSwapContract(args):
    if check_owners(ctx, 1):
        contract = args[0]
        if len(contract) == 20:
            Put(ctx, SWAP_CONTRACT_KEY, contract)
            return True 
    return False


def validateNeoAddr(addr):
    if len(addr) != 20:
        raise Exception("Invalid Neo Addr")
    return True

def validateEthAddr(addr):
    if len(addr) != 40:
        raise Exception("Invalid Eth Addr")
    return True

def getSwapContract():
    contract = Get(ctx, SWAP_CONTRACT_KEY)
    if len(contract) == 20:
        return contract
    raise Exception("Swap contract not set")
