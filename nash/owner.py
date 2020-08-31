from boa.interop.Neo.Storage import *
from boa.interop.Neo.Runtime import CheckWitness


# Mainnet token owners
# TOKEN_OWNER1 = b'P}\xd1\xf0\x0e0\xe7\x95Z\xb8\xb3Ip\x7fB\xfa+e7k'
# TOKEN_OWNER2 = b'Q\xb8$\xa5f\xa6ECu\x9c\xd5\xc9X\xc1\x93\xaf\xa4\xd0\xb8\xfb'
# TOKEN_OWNER3 = b'\x99>:\x81\x00-KZV\xac\x98\x08\xce\xec\x1f\xef\xcb.\xbc\xf5'
# TOKEN_OWNER4 = b'\xed\xcf\xa8\x03Vl\x06\x00\xa6\x82\xd6\xc8\x9a\xb4\xd05\xe13F\xba'
# TOKEN_OWNER5 = b'\xe3\x9cZ\x9e\x04u\x1b\xfb\x85\xdf\xd0\xb6\x07vl\xdc\xb9\x95q\x9f'
# ADMIN_ADDRESS = b'!nG\xf2\xbf\xb0\xb7\x0fB\x99_\n%\x14AQ Aa\xd7'


# Testing token owners
TOKEN_OWNER1 = b'y\xd0C*\xd9\x00\xb7#\xc3.\x1c\x17\xb5.\xeeX\x1el\xbfW'
TOKEN_OWNER2 = b'_\xf9\x8dK,\xe0\xfa_\xc8\xee\xc6\x80\xfaMK\xa3\xfc5\xc2\xf9'
TOKEN_OWNER3 = b'B\xea#\xdb\xf1LS"\xa7\x93\x02\xcc|\x00\xc39\x80y\xa5\xa8'
TOKEN_OWNER4 = b'\x14\x8c5l\xec#\x14\xb3\xac\xa4\x1e\xe7\xd3\x82\xa0\x965\x9c\xce\xf9'
TOKEN_OWNER5 = b'\xc0[\xd5\x02\x8c\x88\x89,4~\xe7H\xc3o\x8d3;\x94n\xb0'

    
def initialize_owners(ctx):
    """
    Initializes the owners from the hard coded version in the contract
    to a storage based version, so that owners can be swapped in case
    an address in compromised or otherwise changed.

    :param ctx: StorageContext
    :return:
    """
    if not Get(ctx, 'owners_initialized'):

        Put(ctx, 'owner1', TOKEN_OWNER1)
        Put(ctx, 'owner2', TOKEN_OWNER2)
        Put(ctx, 'owner3', TOKEN_OWNER3)
        Put(ctx, 'owner4', TOKEN_OWNER4)
        Put(ctx, 'owner5', TOKEN_OWNER5)

        Put(ctx, 'owners_initialized', True)
        return True

    return False

def is_owner_str(owner):
    """
    Determines whether a string is a valid owner string

    :param owner: string identifying an owner
    :return: bool
    """
    if owner == 'owner1' or owner == 'owner2' or owner == 'owner3' or owner == 'owner4' or owner == 'owner5':
        return True
    return False


def get_owners(ctx):
    """
    Retrieves the current list of owners from storage

    :param ctx: StorageContext
    :return: list: a list of owners
    """
    return [Get(ctx, 'owner1'), Get(ctx, 'owner2'), Get(ctx, 'owner3'), Get(ctx, 'owner4'), Get(ctx, 'owner5')]

def check_owners(ctx, required):
    """

    Determines whether or not this transaction was signed with at least 3 of 5 owner signatures

    :param ctx: StorageContext
    :return: bool
    """
    if not Get(ctx, 'owners_initialized'):
        print("Please run initializeOwners")
        return False

    total = 0

    owners = get_owners(ctx)
    for owner in owners:
        if CheckWitness(owner):
            total += 1
    return total >= required


def switch_owner(ctx, args):
    """
    Switch the script hash of an owner to a new one.
    Requires full owner permission ( 3 of 5 )

    :param args: a list of arguments with the owner name first ( eg 'owner1') and a script hash second
    :return: bool
    """
    if not check_owners(ctx, 3):
        return False

    if len(args) != 2:
        return False

    which_owner = args[0]

    if not is_owner_str(which_owner):
        return False

    new_value = args[1]

    if len(new_value) == 20:
        Put(ctx, which_owner, new_value)
        return True

    return False
