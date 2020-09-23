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

OnSwapToEth = RegisterAction("onSwapToEth", "addr", "ethAddr", "amount", "swapId")
OnSwapFromEth = RegisterAction("onSwapFromEth", "addr", "ethAddr", "amount", "swapId")

SWAP_CONTRACT_KEY= 'swapContract'
SWAPID_PREFIX = 'swapId'
SWAP_COUNTER = 'swapCounter'

# Minimum amount to swap is 500 NEX
MIN_SWAP_AMOUNT = 50000000000

# Number of admins required for sensitive actions
# This will be changed to 3 for mainnet
# but kept at 1 for testing
ADMINS_REQUIRED = 1

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
        # This is used in case a contract migration is needed ( for example NEO3 transition)
        if check_owners(ctx, 4):
            return True
        return False

    elif trigger == Application():

        if operation == 'swapToEth':
            if len(args) == 3:
                return swapToEth(args)
            raise Exception("Invalid argument length")

        elif operation == 'swapFromEth':
            if len(args) == 4:
                return swapFromEth(args)
            raise Exception("Invalid argument length")

        elif operation == 'totalSwapped':
            return getTotalSwapped()

        # owner / admin methods
        elif operation == 'initializeOwners':
            return initialize_owners(ctx)

        elif operation == 'setSwapTokenContract':
            if len(args) == 1:                
                return setSwapContract(args)
            raise Exception('Invalid argument length')

        elif operation == 'setMinter':
            if len(args) == 1:                
                return setMinter(args)
            raise Exception('Invalid argument length')

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
    
    if amount < MIN_SWAP_AMOUNT:
        raise Exception("Need to swap at least 500 NEX")

    validateAddr(ethAddr)
    validateAddr(addr)

    tx = GetScriptContainer()
    txHash = tx.Hash
    replayCheck = concat(txHash, addr)

    swapId = Get(ctx, SWAP_COUNTER)

    if Get(ctx, replayCheck) > 0:
        raise Exception("Already swap for this transaction and address")

    if CheckWitness(addr):

        args = [addr, GetExecutingScriptHash(), amount]

        transferOfTokens = DynamicAppCall(getSwapContract(), 'transferFrom', args)

        if transferOfTokens:
            swapId = swapId +1
            Put(ctx, SWAP_COUNTER, swapId)
            Put(ctx, replayCheck, 1)
            OnSwapToEth(addr, ethAddr, amount, swapId)
            return True

    raise Exception("Could not transfer tokens to swap contract")



def swapFromEth(args):
    """
    Only admin may execute a swap from eth
    """
    if check_minter(ctx):
        addr = args[0] # Neo Address to send NEX to 
        ethAddr = args[1]
        amount = args[2]
        swapId = args[3] # integer

        swapIdStorage = concat(SWAPID_PREFIX, swapId)

        # Prevent admin from accidentally performing swap back more than once
        if Get(ctx, swapIdStorage) > 0:
            raise Exception("Already swap for this transaction and address")

        validateAddr(ethAddr)
        validateAddr(addr)

        totalAvailable = getTotalSwapped()
        if totalAvailable < amount:
            raise Exception("Can not swap back from eth tokens that were never swapped")

        ## transfer back to user
        args = [GetExecutingScriptHash(), addr, amount]

        transferOfTokens = DynamicAppCall(getSwapContract(), 'transfer', args)
        if transferOfTokens:
            Put(ctx, swapIdStorage, 1)
            OnSwapFromEth(addr,ethAddr,amount,swapId)
            return True

    return False


def getTotalSwapped():
    tokenContract = getSwapContract()
    contractAddress = GetExecutingScriptHash()
    args = [contractAddress]
    balance = DynamicAppCall(tokenContract,'balanceOf',args)

    return balance

def setSwapContract(args):
    if check_owners(ctx, ADMINS_REQUIRED):
        contract = args[0]
        if len(contract) == 20:
            Put(ctx, SWAP_CONTRACT_KEY, contract)
            return True 
    return False

def setMinter(args):
    if check_owners(ctx, ADMINS_REQUIRED):
        minter = args[0]
        if len(minter) == 20:
            Put(ctx, MINTER_ROLE, minter)
            return True 
    return False

def validateAddr(addr):
    if len(addr) != 20:
        raise Exception("Invalid Addr")
    return True

def getSwapContract():
    contract = Get(ctx, SWAP_CONTRACT_KEY)
    if len(contract) == 20:
        return contract
    raise Exception("Swap contract not set")
