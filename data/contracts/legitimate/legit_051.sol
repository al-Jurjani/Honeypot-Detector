// ---- .venv/lib/pypy3.11/site-packages/snekmate/auth/ownable.vy ----
# pragma version ~=0.4.3
# pragma nonreentrancy off
"""
@title Owner-Based Access Control Functions
@custom:contract-name ownable
@license GNU Affero General Public License v3.0 only
@author pcaversaccio
@notice These functions can be used to implement a basic access
        control mechanism, where there is an account (an owner)
        that can be granted exclusive access to specific functions.
        By default, the owner account will be the one that deploys
        the contract. This can later be changed with `transfer_ownership`.
        An exemplary integration can be found in the ERC-20 implementation here:
        https://github.com/pcaversaccio/snekmate/blob/main/src/snekmate/tokens/erc20.vy.
        The implementation is inspired by OpenZeppelin's implementation here:
        https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/access/Ownable.sol.
"""


# @dev Returns the address of the current owner.
# @notice If you declare a variable as `public`,
# Vyper automatically generates an `external`
# getter function for the variable.
owner: public(address)


# @dev Emitted when the ownership is transferred
# from `previous_owner` to `new_owner`.
event OwnershipTransferred:
    previous_owner: indexed(address)
    new_owner: indexed(address)


@deploy
@payable
def __init__():
    """
    @dev To omit the opcodes for checking the `msg.value`
         in the creation-time EVM bytecode, the constructor
         is declared as `payable`.
    @notice The `owner` role will be assigned to
            the `msg.sender`.
    """
    self._transfer_ownership(msg.sender)


@external
def transfer_ownership(new_owner: address):
    """
    @dev Transfers the ownership of the contract
         to a new account `new_owner`.
    @notice Note that this function can only be
            called by the current `owner`. Also,
            the `new_owner` cannot be the zero address.
    @param new_owner The 20-byte address of the new owner.
    """
    self._check_owner()
    assert new_owner != empty(address), "ownable: new owner is the zero address"
    self._transfer_ownership(new_owner)


@external
def renounce_ownership():
    """
    @dev Leaves the contract without an owner.
    @notice Renouncing ownership will leave the
            contract without an owner, thereby
            removing any functionality that is
            only available to the owner.
    """
    self._check_owner()
    self._transfer_ownership(empty(address))


@internal
def _check_owner():
    """
    @dev Throws if the sender is not the owner.
    """
    assert msg.sender == self.owner, "ownable: caller is not the owner"


@internal
def _transfer_ownership(new_owner: address):
    """
    @dev Transfers the ownership of the contract
         to a new account `new_owner`.
    @notice This is an `internal` function without
            access restriction.
    @param new_owner The 20-byte address of the new owner.
    """
    old_owner: address = self.owner
    self.owner = new_owner
    log OwnershipTransferred(previous_owner=old_owner, new_owner=new_owner)


// ---- .venv/lib/pypy3.11/site-packages/snekmate/tokens/interfaces/IERC20Permit.vyi ----
# pragma version ~=0.4.3
"""
@title EIP-2612 Interface Definition
@custom:contract-name IERC20Permit
@license GNU Affero General Public License v3.0 only
@author pcaversaccio
@notice The `permit` function implements approvals via
        EIP-712 secp256k1 signatures:
        https://eips.ethereum.org/EIPS/eip-2612.
        The `permit` function allows users to modify
        the allowance mapping using a signed message
        (via secp256k1 signatures), instead of through
        `msg.sender`. By not relying on `approve`,
        the token holder's account does not need to
        send a transaction and therefore does not need
        to hold ether, enabling important use cases such
        as meta-transactions.

        On how to use interfaces in Vyper, please visit:
        https://vyper.readthedocs.io/en/latest/interfaces.html#interfaces.
"""


@external
def permit(owner: address, spender: address, amount: uint256, deadline: uint256, v: uint8, r: bytes32, s: bytes32):
    """
    @dev Sets `amount` as the allowance of `spender`
         over `owner`'s tokens, given `owner`'s signed
         approval.
    @notice Note that `spender` cannot be the zero address.
            Also, `deadline` must be a block timestamp in
            the future. `v`, `r`, and `s` must be a valid
            secp256k1 signature from `owner` over the
            EIP-712-formatted function arguments. Eventually,
            the signature must use `owner`'s current nonce.
    @param owner The 20-byte owner address.
    @param spender The 20-byte spender address.
    @param amount The 32-byte token amount that is
           allowed to be spent by the `spender`.
    @param deadline The 32-byte block timestamp up
           which the `spender` is allowed to spend `amount`.
    @param v The secp256k1 1-byte signature parameter `v`.
    @param r The secp256k1 32-byte signature parameter `r`.
    @param s The secp256k1 32-byte signature parameter `s`.
    """
    ...


@external
@view
def nonces(owner: address) -> uint256:
    """
    @dev Returns the current on-chain tracked nonce of `owner`.
    @param owner The 20-byte owner address.
    @return uint256 The 32-byte owner nonce.
    """
    ...


@external
@view
def DOMAIN_SEPARATOR() -> bytes32:
    """
    @dev Returns the domain separator for the current chain.
    @return bytes32 The 32-byte domain separator.
    """
    ...


// ---- .venv/lib/pypy3.11/site-packages/snekmate/utils/interfaces/IERC5267.vyi ----
# pragma version ~=0.4.3
"""
@title EIP-5267 Interface Definition
@custom:contract-name IERC5267
@license GNU Affero General Public License v3.0 only
@author pcaversaccio
@notice The ERC-5267 standard complements the EIP-712 standard
        by standardising how contracts should publish the fields
        and values that describe their domain. This enables
        applications to retrieve this description and generate
        appropriate domain separators in a general way, and thus
        integrate EIP-712 signatures securely and scalably. For
        more details, please refer to:
        https://eips.ethereum.org/EIPS/eip-5267.

        Note that Vyper interfaces that implement functions
        with return values that require an upper bound (e.g.
        `Bytes`, `DynArray`, or `String`), the upper bound
        defined in the interface represents the lower bound
        of the implementation:
        https://github.com/vyperlang/vyper/pull/3205.

        On how to use interfaces in Vyper, please visit:
        https://vyper.readthedocs.io/en/latest/interfaces.html#interfaces.
"""


# @dev May be emitted to signal that the domain could
# have changed.
event EIP712DomainChanged:
    pass


@external
@view
def eip712Domain() -> (bytes1, String[50], String[20], uint256, address, bytes32, DynArray[uint256, 32]):
    """
    @dev Returns the fields and values that describe the domain
         separator used by this contract for EIP-712 signatures.
    @notice The bits in the 1-byte bit map are read from the least
            significant to the most significant, and fields are indexed
            in the order that is specified by EIP-712, identical to the
            order in which they are listed in the function type.
    @return bytes1 The 1-byte bit map where bit `i` is set to `1`
            if and only if domain field `i` is present (`0 ≤ i ≤ 4`).
    @return String The maximum 50-character user-readable string name
            of the signing domain, i.e. the name of the dApp or protocol.
    @return String The maximum 20-character current main version of
            the signing domain. Signatures from different versions are
            not compatible.
    @return uint256 The 32-byte EIP-155 chain ID.
    @return address The 20-byte address of the verifying contract.
    @return bytes32 The 32-byte disambiguation salt for the protocol.
    @return DynArray The 32-byte array of EIP-712 extensions.
    """
    ...


// ---- .venv/lib/pypy3.11/site-packages/snekmate/utils/ecdsa.vy ----
# pragma version ~=0.4.3
# pragma nonreentrancy off
"""
@title Elliptic Curve Digital Signature Algorithm (ECDSA) Secp256k1-Based Functions
@custom:contract-name ecdsa
@license GNU Affero General Public License v3.0 only
@author pcaversaccio
@notice These functions can be used to verify that a message was signed by
        the holder of the private key of a given address. All cryptographic
        calculations are based on the Ethereum-native secp256k1 elliptic curve
        (see https://en.bitcoin.it/wiki/Secp256k1). For verification functions
        based on the NIST P-256 elliptic curve (also known as secp256r1), see
        the {p256} contract. The implementation is inspired by OpenZeppelin's
        implementation here:
        https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/utils/cryptography/ECDSA.sol.
@custom:security Signatures must not be used as unique identifiers since the
                 `ecrecover` EVM precompile allows for malleable (non-unique)
                 signatures (see EIP-2: https://eips.ethereum.org/EIPS/eip-2)
                 or signatures can be malleablised using EIP-2098:
                 https://eips.ethereum.org/EIPS/eip-2098.
"""


# @dev The malleability threshold used as part of the ECDSA
# verification function.
_MALLEABILITY_THRESHOLD: constant(uint256) = (
    57_896_044_618_658_097_711_785_492_504_343_953_926_418_782_139_537_452_191_302_581_570_759_080_747_168
)


@deploy
@payable
def __init__():
    """
    @dev To omit the opcodes for checking the `msg.value`
         in the creation-time EVM bytecode, the constructor
         is declared as `payable`.
    """
    pass


@internal
@pure
def _recover_sig(hash: bytes32, signature: Bytes[65]) -> address:
    """
    @dev Recovers the signer address from a message digest `hash`
         and the signature `signature`.
    @notice WARNING: This function is vulnerable to a kind of
            signature malleability due to accepting EIP-2098
            compact signatures in addition to the traditional
            65-byte signature format. The potentially affected
            contracts are those that implement signature reuse
            or replay protection by marking the signature itself
            as used rather than the signed message or a nonce
            included in it. A user may take a signature that has
            already been submitted, submit it again in a different
            form, and bypass this protection. Also, see OpenZeppelin's
            security advisory for more information:
            https://github.com/OpenZeppelin/openzeppelin-contracts/security/advisories/GHSA-4h98-2769-gh6h.
    @param hash The 32-byte message digest that was signed.
    @param signature The secp256k1 64/65-byte signature of `hash`.
    @return address The recovered 20-byte signer address.
    """
    sig_length: uint256 = len(signature)
    # 65-byte case: `(r,s,v)` standard signature.
    if sig_length == 65:
        r: uint256 = extract32(signature, empty(uint256), output_type=uint256)
        s: uint256 = extract32(signature, 32, output_type=uint256)
        v: uint256 = convert(slice(signature, 64, 1), uint256)
        return self._try_recover_vrs(hash, v, r, s)
    # 64-byte case: `(r,vs)` signature; see: https://eips.ethereum.org/EIPS/eip-2098.
    elif sig_length == 64:
        r: uint256 = extract32(signature, empty(uint256), output_type=uint256)
        vs: uint256 = extract32(signature, 32, output_type=uint256)
        return self._try_recover_r_vs(hash, r, vs)

    return empty(address)


@internal
@pure
def _recover_vrs(hash: bytes32, v: uint256, r: uint256, s: uint256) -> address:
    """
    @dev Recovers the signer address from a message digest `hash`
         and the secp256k1 signature parameters `v`, `r`, and `s`.
    @param hash The 32-byte message digest that was signed.
    @param v The secp256k1 1-byte signature parameter `v`.
    @param r The secp256k1 32-byte signature parameter `r`.
    @param s The secp256k1 32-byte signature parameter `s`.
    @return address The recovered 20-byte signer address.
    """
    return self._try_recover_vrs(hash, v, r, s)


@internal
@pure
def _try_recover_r_vs(hash: bytes32, r: uint256, vs: uint256) -> address:
    """
    @dev Recovers the signer address from a message digest `hash`
         and the secp256k1 short signature fields `r` and `vs`.
    @notice See https://eips.ethereum.org/EIPS/eip-2098 for the
            compact signature representation.
    @param hash The 32-byte message digest that was signed.
    @param r The secp256k1 32-byte signature parameter `r`.
    @param vs The secp256k1 32-byte short signature field of `v` and `s`.
    @return address The recovered 20-byte signer address.
    """
    s: uint256 = vs & convert(max_value(int256), uint256)
    # We do not check for an overflow here, as the shift operation
    # `vs >> 255` results in `0` or `1`.
    v: uint256 = unsafe_add(vs >> 255, 27)
    return self._try_recover_vrs(hash, v, r, s)


@internal
@pure
def _try_recover_vrs(hash: bytes32, v: uint256, r: uint256, s: uint256) -> address:
    """
    @dev Recovers the signer address from a message digest `hash`
         and the secp256k1 signature parameters `v`, `r`, and `s`.
    @notice All client implementations of the precompile `ecrecover`
            check if the value of `v` is `27` or `28`. The references
            for the different client implementations can be found here:
            https://github.com/ethereum/yellowpaper/pull/860. Thus,
            the signature check on the value of `v` is neglected.
    @param hash The 32-byte message digest that was signed.
    @param v The secp256k1 1-byte signature parameter `v`.
    @param r The secp256k1 32-byte signature parameter `r`.
    @param s The secp256k1 32-byte signature parameter `s`.
    @return address The recovered 20-byte signer address.
    """
    assert s <= _MALLEABILITY_THRESHOLD, "ecdsa: invalid signature `s` value"

    signer: address = ecrecover(hash, v, r, s)
    assert signer != empty(address), "ecdsa: invalid signature"

    return signer


// ---- .venv/lib/pypy3.11/site-packages/snekmate/utils/message_hash_utils.vy ----
# pragma version ~=0.4.3
# pragma nonreentrancy off
"""
@title Signature Message Hash Utility Functions
@custom:contract-name message_hash_utils
@license GNU Affero General Public License v3.0 only
@author pcaversaccio
@notice These functions can be used to generate message hashes that conform
        to the EIP-191 (https://eips.ethereum.org/EIPS/eip-191) as well as
        EIP-712 (https://eips.ethereum.org/EIPS/eip-712) specifications. The
        implementation is inspired by OpenZeppelin's implementation here:
        https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/utils/cryptography/MessageHashUtils.sol.
"""


@deploy
@payable
def __init__():
    """
    @dev To omit the opcodes for checking the `msg.value`
         in the creation-time EVM bytecode, the constructor
         is declared as `payable`.
    """
    pass


@internal
@pure
def _to_eth_signed_message_hash(hash: bytes32) -> bytes32:
    """
    @dev Returns an Ethereum signed message from a 32-byte
         message digest `hash`.
    @notice This function returns a 32-byte hash that
            corresponds to the one signed with the JSON-RPC method:
            https://ethereum.org/en/developers/docs/apis/json-rpc/#eth_sign.
            This method is part of EIP-191:
            https://eips.ethereum.org/EIPS/eip-191.
    @param hash The 32-byte message digest.
    @return bytes32 The 32-byte Ethereum signed message.
    """
    return keccak256(concat(b"\x19Ethereum Signed Message:\n32", hash))


@internal
@view
def _to_data_with_intended_validator_hash_self(data: Bytes[1_024]) -> bytes32:
    """
    @dev Returns an Ethereum signed data with this contract
         as the intended validator and a maximum 1,024-byte
         payload `data`.
    @notice This function structures the data according to
            the version `0x00` of EIP-191:
            https://eips.ethereum.org/EIPS/eip-191#version-0x00.
    @param data The maximum 1,024-byte data to be signed.
    @return bytes32 The 32-byte Ethereum signed data.
    """
    return self._to_data_with_intended_validator_hash(self, data)


@internal
@pure
def _to_data_with_intended_validator_hash(validator: address, data: Bytes[1_024]) -> bytes32:
    """
    @dev Returns an Ethereum signed data with `validator` as
         the intended validator and a maximum 1,024-byte payload
         `data`.
    @notice This function structures the data according to
            the version `0x00` of EIP-191:
            https://eips.ethereum.org/EIPS/eip-191#version-0x00.
    @param validator The 20-byte intended validator address.
    @param data The maximum 1,024-byte data to be signed.
    @return bytes32 The 32-byte Ethereum signed data.
    """
    return keccak256(concat(x"1900", convert(validator, bytes20), data))


@internal
@pure
def _to_typed_data_hash(domain_separator: bytes32, struct_hash: bytes32) -> bytes32:
    """
    @dev Returns an Ethereum signed typed data from a 32-byte
         `domain_separator` and a 32-byte `struct_hash`.
    @notice This function returns a 32-byte hash that
            corresponds to the one signed with the JSON-RPC method:
            https://eips.ethereum.org/EIPS/eip-712#specification-of-the-eth_signtypeddata-json-rpc.
            This method is part of EIP-712:
            https://eips.ethereum.org/EIPS/eip-712.
    @param domain_separator The 32-byte domain separator that is
           used as part of the EIP-712 encoding scheme.
    @param struct_hash The 32-byte struct hash that is used as
           part of the EIP-712 encoding scheme. See the definition:
           https://eips.ethereum.org/EIPS/eip-712#definition-of-hashstruct.
    @return bytes32 The 32-byte Ethereum signed typed data.
    """
    return keccak256(concat(x"1901", domain_separator, struct_hash))


// ---- .venv/lib/pypy3.11/site-packages/snekmate/utils/eip712_domain_separator.vy ----
# pragma version ~=0.4.3
# pragma nonreentrancy off
"""
@title EIP-712 Domain Separator
@custom:contract-name eip712_domain_separator
@license GNU Affero General Public License v3.0 only
@author pcaversaccio
@notice These functions are part of EIP-712: https://eips.ethereum.org/EIPS/eip-712.
        These functions implement the version of encoding known
        as "v4" as implemented by the JSON-RPC method:
        https://docs.metamask.io/guide/signing-data.html#sign-typed-data-v4.
        In addition, this contract also implements EIP-5267:
        https://eips.ethereum.org/EIPS/eip-5267.
        The implementation is inspired by OpenZeppelin's implementation here:
        https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/utils/cryptography/EIP712.sol.
"""


# @dev We import and implement the `IERC5267` interface,
# which is written using standard Vyper syntax.
from .interfaces import IERC5267
implements: IERC5267


# @dev We import the `message_hash_utils` module.
# @notice Please note that the `message_hash_utils`
# module is stateless and therefore does not require
# the `uses` keyword for usage.
from . import message_hash_utils


# @dev The 32-byte type hash for the EIP-712 domain separator.
_TYPE_HASH: constant(bytes32) = keccak256(
    "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
)


# @dev Caches the domain separator as an `immutable`
# value, but also stores the corresponding chain ID
# to invalidate the cached domain separator if the
# chain ID changes.
_CACHED_DOMAIN_SEPARATOR: immutable(bytes32)
_CACHED_CHAIN_ID: immutable(uint256)


# @dev Caches `self` to `immutable` storage to avoid
# potential issues if a vanilla contract is used in
# a `delegatecall` context.
_CACHED_SELF: immutable(address)


# @dev `immutable` variables to store the (hashed)
# name and (hashed) version during contract creation.
_NAME: immutable(String[50])
_HASHED_NAME: immutable(bytes32)
_VERSION: immutable(String[20])
_HASHED_VERSION: immutable(bytes32)


@deploy
@payable
def __init__(name_: String[50], version_: String[20]):
    """
    @dev Initialises the domain separator and the parameter caches.
         To omit the opcodes for checking the `msg.value` in the
         creation-time EVM bytecode, the constructor is declared as
         `payable`.
    @notice The definition of the domain separator can be found here:
            https://eips.ethereum.org/EIPS/eip-712#definition-of-domainseparator.
            Since the Vyper design requires strings of fixed size,
            we arbitrarily set the maximum length for `name` to 50
            characters and `version` to 20 characters.
    @param name_ The maximum 50-character user-readable string name
           of the signing domain, i.e. the name of the dApp or protocol.
    @param version_ The maximum 20-character current main version of
           the signing domain. Signatures from different versions are
           not compatible.
    """
    _NAME = name_
    _VERSION = version_
    _HASHED_NAME = keccak256(name_)
    _HASHED_VERSION = keccak256(version_)
    _CACHED_DOMAIN_SEPARATOR = self._build_domain_separator()
    _CACHED_CHAIN_ID = chain.id
    _CACHED_SELF = self


@external
@view
def eip712Domain() -> (bytes1, String[50], String[20], uint256, address, bytes32, DynArray[uint256, 32]):
    """
    @dev Returns the fields and values that describe the domain
         separator used by this contract for EIP-712 signatures.
    @notice The bits in the 1-byte bit map are read from the least
            significant to the most significant, and fields are indexed
            in the order that is specified by EIP-712, identical to the
            order in which they are listed in the function type.
    @return bytes1 The 1-byte bit map where bit `i` is set to `1`
            if and only if domain field `i` is present (`0 ≤ i ≤ 4`).
    @return String The maximum 50-character user-readable string name
            of the signing domain, i.e. the name of the dApp or protocol.
    @return String The maximum 20-character current main version of
            the signing domain. Signatures from different versions are
            not compatible.
    @return uint256 The 32-byte EIP-155 chain ID.
    @return address The 20-byte address of the verifying contract.
    @return bytes32 The 32-byte disambiguation salt for the protocol.
    @return DynArray The 32-byte array of EIP-712 extensions.
    """
    # Note that `0x0f` equals `01111`.
    return (0x0f, _NAME, _VERSION, chain.id, self, empty(bytes32), empty(DynArray[uint256, 32]))


@internal
@view
def _domain_separator_v4() -> bytes32:
    """
    @dev Returns the domain separator for the current chain.
    @return bytes32 The 32-byte domain separator.
    """
    if self == _CACHED_SELF and chain.id == _CACHED_CHAIN_ID:
        return _CACHED_DOMAIN_SEPARATOR

    return self._build_domain_separator()


@internal
@view
def _build_domain_separator() -> bytes32:
    """
    @dev Builds the domain separator for the current chain.
    @return bytes32 The 32-byte domain separator.
    """
    return keccak256(abi_encode(_TYPE_HASH, _HASHED_NAME, _HASHED_VERSION, chain.id, self))


@internal
@view
def _hash_typed_data_v4(struct_hash: bytes32) -> bytes32:
    """
    @dev Returns the hash of the fully encoded EIP-712
         message for this domain.
    @notice The definition of the hashed struct can be found here:
            https://eips.ethereum.org/EIPS/eip-712#definition-of-hashstruct.
    @param struct_hash The 32-byte hashed struct.
    @return bytes32 The 32-byte fully encoded EIP712
            message hash for this domain.
    """
    return message_hash_utils._to_typed_data_hash(self._domain_separator_v4(), struct_hash)


// ---- .venv/lib/pypy3.11/site-packages/snekmate/tokens/erc20.vy ----
# pragma version ~=0.4.3
# pragma nonreentrancy off
"""
@title Modern and Gas-Efficient ERC-20 + EIP-2612 Implementation
@custom:contract-name erc20
@license GNU Affero General Public License v3.0 only
@author pcaversaccio
@notice These functions implement the ERC-20
        standard interface:
        - https://eips.ethereum.org/EIPS/eip-20.
        In addition, the following functions have
        been added for convenience:
        - `name` (`external` `view` function),
        - `symbol` (`external` `view` function),
        - `decimals` (`external` `view` function),
        - `burn` (`external` function),
        - `burn_from` (`external` function),
        - `is_minter` (`external` `view` function),
        - `mint` (`external` function),
        - `set_minter` (`external` function),
        - `permit` (`external` function),
        - `nonces` (`external` `view` function),
        - `DOMAIN_SEPARATOR` (`external` `view` function),
        - `eip712Domain` (`external` `view` function),
        - `owner` (`external` `view` function),
        - `transfer_ownership` (`external` function),
        - `renounce_ownership` (`external` function),
        - `_before_token_transfer` (`internal` function),
        - `_after_token_transfer` (`internal` function).
        The `permit` function implements approvals via
        EIP-712 secp256k1 signatures:
        https://eips.ethereum.org/EIPS/eip-2612.
        In addition, this contract also implements the EIP-5267
        function `eip712Domain`:
        https://eips.ethereum.org/EIPS/eip-5267.
        The implementation is inspired by OpenZeppelin's
        implementation here:
        https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/token/ERC20/ERC20.sol,
        as well as by ApeAcademy's implementation here:
        https://github.com/ApeAcademy/ERC20/blob/main/%7B%7Bcookiecutter.project_name%7D%7D/contracts/Token.vy.
@custom:security This ERC-20 implementation allows the commonly known
                 address poisoning attack, where `transferFrom` instructions
                 are executed from arbitrary addresses with an `amount` of `0`.
                 However, this poisoning attack is not an on-chain vulnerability.
                 All assets are safe. It is an off-chain log interpretation issue.
                 The main reason why we do not disallow address poisonig is that
                 we do not want to potentially break any DeFi composability.
                 This issue has been extensively discussed here:
                 https://github.com/pcaversaccio/snekmate/issues/51,
                 as well as in the OpenZeppelin repository:
                 https://github.com/OpenZeppelin/openzeppelin-contracts/issues/3931.
"""


# @dev We import and implement the `IERC20` interface,
# which is a built-in interface of the Vyper compiler.
from ethereum.ercs import IERC20
implements: IERC20


# @dev We import and implement the `IERC20Detailed` interface,
# which is a built-in interface of the Vyper compiler.
from ethereum.ercs import IERC20Detailed
implements: IERC20Detailed


# @dev We import and implement the `IERC20Permit`
# interface, which is written using standard Vyper
# syntax.
from .interfaces import IERC20Permit
implements: IERC20Permit


# @dev We import and implement the `IERC5267` interface,
# which is written using standard Vyper syntax.
from ..utils.interfaces import IERC5267
implements: IERC5267


# @dev We import and use the `ownable` module.
from ..auth import ownable
uses: ownable


# @dev We import the `ecdsa` module.
# @notice Please note that the `ecdsa` module
# is stateless and therefore does not require
# the `uses` keyword for usage.
from ..utils import ecdsa


# @dev We import and initialise the `eip712_domain_separator` module.
from ..utils import eip712_domain_separator
initializes: eip712_domain_separator


# @dev We export (i.e. the runtime bytecode exposes these
# functions externally, allowing them to be called using
# the ABI encoding specification) the `external` getter
# function `owner` from the `ownable` module as well as the
# function `eip712Domain` from the `eip712_domain_separator`
# module.
# @notice Please note that you must always also export (if
# required by the contract logic) `public` declared `constant`,
# `immutable`, and state variables, for which Vyper automatically
# generates an `external` getter function for the variable.
exports: (
    # @notice This ERC-20 implementation includes the `transfer_ownership`
    # and `renounce_ownership` functions, which incorporate
    # the additional built-in `is_minter` role logic and are
    # therefore not exported from the `ownable` module.
    ownable.owner,
    eip712_domain_separator.eip712Domain,
)


# @dev The 32-byte type hash of the `permit` function.
_PERMIT_TYPE_HASH: constant(bytes32) = keccak256(
    "Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"
)


# @dev Returns the name of the token.
# @notice If you declare a variable as `public`,
# Vyper automatically generates an `external`
# getter function for the variable. Furthermore,
# to preserve consistency with the interface for
# the optional metadata functions of the ERC-20
# standard, we use lower case letters for the
# `immutable` variables `name`, `symbol`, and
# `decimals`.
name: public(immutable(String[25]))


# @dev Returns the symbol of the token.
# @notice See comment on lower case letters
# above at `name`.
symbol: public(immutable(String[5]))


# @dev Returns the decimal places of the token.
# @notice See comment on lower case letters
# above at `name`.
decimals: public(immutable(uint8))


# @dev Returns the amount of tokens owned by an `address`.
balanceOf: public(HashMap[address, uint256])


# @dev Returns the remaining number of tokens that a
# `spender` will be allowed to spend on behalf of
# `owner` through `transferFrom`. This is zero by
# default. This value changes when `approve` or
# `transferFrom` are called.
allowance: public(HashMap[address, HashMap[address, uint256]])


# @dev Returns the amount of tokens in existence.
totalSupply: public(uint256)


# @dev Returns `True` if an `address` has been
# granted the minter role.
is_minter: public(HashMap[address, bool])


# @dev Returns the current on-chain tracked nonce
# of `address`.
nonces: public(HashMap[address, uint256])


# @dev Emitted when the status of a `minter`
# address is changed.
event RoleMinterChanged:
    minter: indexed(address)
    status: bool


@deploy
@payable
def __init__(
    name_: String[25], symbol_: String[5], decimals_: uint8, name_eip712_: String[50], version_eip712_: String[20]
):
    """
    @dev To omit the opcodes for checking the `msg.value`
         in the creation-time EVM bytecode, the constructor
         is declared as `payable`.
    @notice At initialisation time, the `owner` role will be
            assigned to the `msg.sender` since we `uses` the
            `ownable` module, which implements the aforementioned
            logic at contract creation time.
    @param name_ The maximum 25-character user-readable
           string name of the token.
    @param symbol_ The maximum 5-character user-readable
           string symbol of the token.
    @param decimals_ The 1-byte decimal places of the token.
    @param name_eip712_ The maximum 50-character user-readable
           string name of the signing domain, i.e. the name
           of the dApp or protocol.
    @param version_eip712_ The maximum 20-character current
           main version of the signing domain. Signatures
           from different versions are not compatible.
    """
    name = name_
    symbol = symbol_
    decimals = decimals_

    self.is_minter[msg.sender] = True
    log RoleMinterChanged(minter=msg.sender, status=True)

    eip712_domain_separator.__init__(name_eip712_, version_eip712_)


@external
def transfer(to: address, amount: uint256) -> bool:
    """
    @dev Moves `amount` tokens from the caller's
         account to `to`.
    @notice Note that `to` cannot be the zero address.
            Also, the caller must have a balance of at
            least `amount`.
    @param to The 20-byte receiver address.
    @param amount The 32-byte token amount to be transferred.
    @return bool The verification whether the transfer succeeded
            or failed. Note that the function reverts instead
            of returning `False` on a failure.
    """
    self._transfer(msg.sender, to, amount)
    return True


@external
def approve(spender: address, amount: uint256) -> bool:
    """
    @dev Sets `amount` as the allowance of `spender`
         over the caller's tokens.
    @notice WARNING: Note that if `amount` is the maximum
            `uint256`, the allowance is not updated on
            `transferFrom`. This is semantically equivalent
            to an infinite approval. Also, `spender` cannot
            be the zero address.

            IMPORTANT: Beware that changing an allowance
            with this method brings the risk that someone
            may use both the old and the new allowance by
            unfortunate transaction ordering. One possible
            solution to mitigate this race condition is to
            first reduce the spender's allowance to `0` and
            set the desired amount afterwards:
            https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729.
    @param spender The 20-byte spender address.
    @param amount The 32-byte token amount that is
           allowed to be spent by the `spender`.
    @return bool The verification whether the approval operation
            succeeded or failed. Note that the function reverts
            instead of returning `False` on a failure.
    """
    self._approve(msg.sender, spender, amount)
    return True


@external
def transferFrom(owner: address, to: address, amount: uint256) -> bool:
    """
    @dev Moves `amount` tokens from `owner`
         to `to` using the allowance mechanism.
         The `amount` is then deducted from the
         caller's allowance.
    @notice Note that `owner` and `to` cannot
            be the zero address. Also, `owner`
            must have a balance of at least `amount`.
            Eventually, the caller must have allowance
            for `owner`'s tokens of at least `amount`.

            WARNING: The function does not update the
            allowance if the current allowance is the
            maximum `uint256`.
    @param owner The 20-byte owner address.
    @param to The 20-byte receiver address.
    @param amount The 32-byte token amount to be transferred.
    @return bool The verification whether the transfer succeeded
            or failed. Note that the function reverts instead
            of returning `False` on a failure.
    """
    self._spend_allowance(owner, msg.sender, amount)
    self._transfer(owner, to, amount)
    return True


@external
def burn(amount: uint256):
    """
    @dev Destroys `amount` tokens from the caller.
    @param amount The 32-byte token amount to be destroyed.
    """
    self._burn(msg.sender, amount)


@external
def burn_from(owner: address, amount: uint256):
    """
    @dev Destroys `amount` tokens from `owner`,
         deducting from the caller's allowance.
    @notice Note that `owner` cannot be the
            zero address. Also, the caller must
            have an allowance for `owner`'s tokens
            of at least `amount`.
    @param owner The 20-byte owner address.
    @param amount The 32-byte token amount to be destroyed.
    """
    self._spend_allowance(owner, msg.sender, amount)
    self._burn(owner, amount)


@external
def mint(owner: address, amount: uint256):
    """
    @dev Creates `amount` tokens and assigns them to `owner`.
    @notice Only authorised minters can access this function.
            Note that `owner` cannot be the zero address.
    @param owner The 20-byte owner address.
    @param amount The 32-byte token amount to be created.
    """
    assert self.is_minter[msg.sender], "erc20: access is denied"
    self._mint(owner, amount)


@external
def set_minter(minter: address, status: bool):
    """
    @dev Adds or removes an address `minter` to/from the
         list of allowed minters. Note that only the
         `owner` can add or remove `minter` addresses.
         Also, the `minter` cannot be the zero address.
         Eventually, the `owner` cannot remove himself
         from the list of allowed minters.
    @param minter The 20-byte minter address.
    @param status The Boolean variable that sets the status.
    """
    ownable._check_owner()
    assert minter != empty(address), "erc20: minter is the zero address"
    # We ensured in the previous step `ownable._check_owner`
    # that `msg.sender` is the `owner`.
    assert minter != msg.sender, "erc20: minter is owner address"
    self.is_minter[minter] = status
    log RoleMinterChanged(minter=minter, status=status)


@external
def permit(owner: address, spender: address, amount: uint256, deadline: uint256, v: uint8, r: bytes32, s: bytes32):
    """
    @dev Sets `amount` as the allowance of `spender`
         over `owner`'s tokens, given `owner`'s signed
         approval.
    @notice Note that `spender` cannot be the zero address.
            Also, `deadline` must be a block timestamp in
            the future. `v`, `r`, and `s` must be a valid
            secp256k1 signature from `owner` over the
            EIP-712-formatted function arguments. Eventually,
            the signature must use `owner`'s current nonce.
    @param owner The 20-byte owner address.
    @param spender The 20-byte spender address.
    @param amount The 32-byte token amount that is
           allowed to be spent by the `spender`.
    @param deadline The 32-byte block timestamp up
           which the `spender` is allowed to spend `amount`.
    @param v The secp256k1 1-byte signature parameter `v`.
    @param r The secp256k1 32-byte signature parameter `r`.
    @param s The secp256k1 32-byte signature parameter `s`.
    """
    assert block.timestamp <= deadline, "erc20: expired deadline"

    current_nonce: uint256 = self.nonces[owner]
    self.nonces[owner] = unsafe_add(current_nonce, 1)

    struct_hash: bytes32 = keccak256(abi_encode(_PERMIT_TYPE_HASH, owner, spender, amount, current_nonce, deadline))
    hash: bytes32 = eip712_domain_separator._hash_typed_data_v4(struct_hash)

    signer: address = ecdsa._recover_vrs(hash, convert(v, uint256), convert(r, uint256), convert(s, uint256))
    assert signer == owner, "erc20: invalid signature"

    self._approve(owner, spender, amount)


@external
@view
def DOMAIN_SEPARATOR() -> bytes32:
    """
    @dev Returns the domain separator for the current chain.
    @return bytes32 The 32-byte domain separator.
    """
    return eip712_domain_separator._domain_separator_v4()


@external
def transfer_ownership(new_owner: address):
    """
    @dev Transfers the ownership of the contract
         to a new account `new_owner`.
    @notice Note that this function can only be
            called by the current `owner`. Also,
            the `new_owner` cannot be the zero address.

            WARNING: The ownership transfer also removes
            the previous owner's minter role and assigns
            the minter role to `new_owner` accordingly.
    @param new_owner The 20-byte address of the new owner.
    """
    ownable._check_owner()
    assert new_owner != empty(address), "erc20: new owner is the zero address"

    self.is_minter[msg.sender] = False
    log RoleMinterChanged(minter=msg.sender, status=False)

    ownable._transfer_ownership(new_owner)
    self.is_minter[new_owner] = True
    log RoleMinterChanged(minter=new_owner, status=True)


@external
def renounce_ownership():
    """
    @dev Leaves the contract without an owner.
    @notice Renouncing ownership will leave the
            contract without an owner, thereby
            removing any functionality that is
            only available to the owner. Note
            that the `owner` is also removed from
            the list of allowed minters.

            WARNING: All other existing `minter`
            addresses will still be able to create
            new tokens. Consider removing all non-owner
            minter addresses first via `set_minter`
            before calling `renounce_ownership`.
    """
    ownable._check_owner()
    self.is_minter[msg.sender] = False
    log RoleMinterChanged(minter=msg.sender, status=False)
    ownable._transfer_ownership(empty(address))


@internal
def _transfer(owner: address, to: address, amount: uint256):
    """
    @dev Moves `amount` tokens from the owner's
         account to `to`.
    @notice Note that `owner` and `to` cannot be
            the zero address. Also, `owner` must
            have a balance of at least `amount`.
    @param owner The 20-byte owner address.
    @param to The 20-byte receiver address.
    @param amount The 32-byte token amount to be transferred.
    """
    assert owner != empty(address), "erc20: transfer from the zero address"
    assert to != empty(address), "erc20: transfer to the zero address"

    self._before_token_transfer(owner, to, amount)

    owner_balanceOf: uint256 = self.balanceOf[owner]
    assert owner_balanceOf >= amount, "erc20: transfer amount exceeds balance"
    self.balanceOf[owner] = unsafe_sub(owner_balanceOf, amount)
    self.balanceOf[to] = unsafe_add(self.balanceOf[to], amount)
    log IERC20.Transfer(sender=owner, receiver=to, value=amount)

    self._after_token_transfer(owner, to, amount)


@internal
def _mint(owner: address, amount: uint256):
    """
    @dev Creates `amount` tokens and assigns
         them to `owner`, increasing the
         total supply.
    @notice This is an `internal` function without
            access restriction. Note that `owner`
            cannot be the zero address.
    @param owner The 20-byte owner address.
    @param amount The 32-byte token amount to be created.
    """
    assert owner != empty(address), "erc20: mint to the zero address"

    self._before_token_transfer(empty(address), owner, amount)

    self.totalSupply += amount
    self.balanceOf[owner] = unsafe_add(self.balanceOf[owner], amount)
    log IERC20.Transfer(sender=empty(address), receiver=owner, value=amount)

    self._after_token_transfer(empty(address), owner, amount)


@internal
def _burn(owner: address, amount: uint256):
    """
    @dev Destroys `amount` tokens from `owner`,
         reducing the total supply.
    @notice Note that `owner` cannot be the
            zero address. Also, `owner` must
            have at least `amount` tokens.
    @param owner The 20-byte owner address.
    @param amount The 32-byte token amount to be destroyed.
    """
    assert owner != empty(address), "erc20: burn from the zero address"

    self._before_token_transfer(owner, empty(address), amount)

    account_balance: uint256 = self.balanceOf[owner]
    assert account_balance >= amount, "erc20: burn amount exceeds balance"
    self.balanceOf[owner] = unsafe_sub(account_balance, amount)
    self.totalSupply = unsafe_sub(self.totalSupply, amount)
    log IERC20.Transfer(sender=owner, receiver=empty(address), value=amount)

    self._after_token_transfer(owner, empty(address), amount)


@internal
def _approve(owner: address, spender: address, amount: uint256):
    """
    @dev Sets `amount` as the allowance of `spender`
         over the `owner`'s tokens.
    @notice Note that `owner` and `spender` cannot
            be the zero address.
    @param owner The 20-byte owner address.
    @param spender The 20-byte spender address.
    @param amount The 32-byte token amount that is
           allowed to be spent by the `spender`.
    """
    assert owner != empty(address), "erc20: approve from the zero address"
    assert spender != empty(address), "erc20: approve to the zero address"

    self.allowance[owner][spender] = amount
    log IERC20.Approval(owner=owner, spender=spender, value=amount)


@internal
def _spend_allowance(owner: address, spender: address, amount: uint256):
    """
    @dev Updates `owner`'s allowance for `spender`
         based on spent `amount`.
    @notice WARNING: Note that it does not update the
            allowance `amount` in case of infinite
            allowance. Also, it reverts if not enough
            allowance is available.
    @param owner The 20-byte owner address.
    @param spender The 20-byte spender address.
    @param amount The 32-byte token amount that is
           allowed to be spent by the `spender`.
    """
    current_allowance: uint256 = self.allowance[owner][spender]
    if current_allowance < max_value(uint256):
        # The following line allows the commonly known address
        # poisoning attack, where `transferFrom` instructions
        # are executed from arbitrary addresses with an `amount`
        # of `0`. However, this poisoning attack is not an on-chain
        # vulnerability. All assets are safe. It is an off-chain
        # log interpretation issue.
        assert current_allowance >= amount, "erc20: insufficient allowance"
        self._approve(owner, spender, unsafe_sub(current_allowance, amount))


@internal
def _before_token_transfer(owner: address, to: address, amount: uint256):
    """
    @dev Hook that is called before any transfer of tokens.
         This includes minting and burning.
    @notice The calling conditions are:
            - when `owner` and `to` are both non-zero,
              `amount` of `owner`'s tokens will be
              transferred to `to`,
            - when `owner` is zero, `amount` tokens will
              be minted for `to`,
            - when `to` is zero, `amount` of `owner`'s
              tokens will be burned,
            - `owner` and `to` are never both zero.
    @param owner The 20-byte owner address.
    @param to The 20-byte receiver address.
    @param amount The 32-byte token amount to be transferred.
    """
    pass


@internal
def _after_token_transfer(owner: address, to: address, amount: uint256):
    """
    @dev Hook that is called after any transfer of tokens.
         This includes minting and burning.
    @notice The calling conditions are:
            - when `owner` and `to` are both non-zero,
              `amount` of `owner`'s tokens has been
              transferred to `to`,
            - when `owner` is zero, `amount` tokens
              have been minted for `to`,
            - when `to` is zero, `amount` of `owner`'s
              tokens have been burned,
            - `owner` and `to` are never both zero.
    @param owner The 20-byte owner address.
    @param to The 20-byte receiver address.
    @param amount The 32-byte token amount that has
           been transferred.
    """
    pass


// ---- .venv/lib/pypy3.11/site-packages/snekmate/utils/math.vy ----
# pragma version ~=0.4.3
# pragma nonreentrancy off
"""
@title Standard Mathematical Utility Functions
@custom:contract-name math
@license GNU Affero General Public License v3.0 only
@author pcaversaccio
@custom:coauthor bout3fiddy
@notice These functions implement standard mathematical utility
        functions that are missing in the Vyper language. If a
        function is inspired by an existing implementation, it
        is properly referenced in the function docstring. The
        following functions have been added for convenience:
        - `_uint256_average` (`internal` `pure` function),
        - `_int256_average` (`internal` `pure` function),
        - `_ceil_div` (`internal` `pure` function),
        - `_signum` (`internal` `pure` function),
        - `_mul_div` (`internal` `pure` function),
        - `_log2` (`internal` `pure` function),
        - `_log10` (`internal` `pure` function),
        - `_log256` (`internal` `pure` function),
        - `_wad_ln` (`internal` `pure` function),
        - `_wad_exp` (`internal` `pure` function),
        - `_cbrt` (`internal` `pure` function),
        - `_wad_cbrt` (`internal` `pure` function).
"""


@deploy
@payable
def __init__():
    """
    @dev To omit the opcodes for checking the `msg.value`
         in the creation-time EVM bytecode, the constructor
         is declared as `payable`.
    """
    pass


@internal
@pure
def _uint256_average(x: uint256, y: uint256) -> uint256:
    """
    @dev Returns the average of two 32-byte unsigned integers.
    @notice Note that the result is rounded towards zero. For
            more details on finding the average of two unsigned
            integers without an overflow, please refer to:
            https://devblogs.microsoft.com/oldnewthing/20220207-00/?p=106223.
    @param x The first 32-byte unsigned integer of the data set.
    @param y The second 32-byte unsigned integer of the data set.
    @return uint256 The 32-byte average (rounded towards zero) of
            `x` and `y`.
    """
    return unsafe_add(x & y, (x ^ y) >> 1)


@internal
@pure
def _int256_average(x: int256, y: int256) -> int256:
    """
    @dev Returns the average of two 32-byte signed integers.
    @notice Note that the result is rounded towards infinity.
            For more details on finding the average of two signed
            integers without an overflow, please refer to:
            https://patents.google.com/patent/US6007232A/en.
    @param x The first 32-byte signed integer of the data set.
    @param y The second 32-byte signed integer of the data set.
    @return int256 The 32-byte average (rounded towards infinity)
            of `x` and `y`.
    """
    return unsafe_add(unsafe_add(x >> 1, y >> 1), x & y & 1)


@internal
@pure
def _ceil_div(x: uint256, y: uint256) -> uint256:
    """
    @dev Calculates "ceil(x / y)" for any strictly positive `y`.
    @notice The implementation is inspired by OpenZeppelin's
            implementation here:
            https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/utils/math/Math.sol.
    @param x The 32-byte numerator.
    @param y The 32-byte denominator.
    @return uint256 The 32-byte rounded up result of "x/y".
    """
    assert y != empty(uint256), "math: ceil_div division by zero"
    # Due to a known compiler bug (https://github.com/vyperlang/vyper/issues/3480),
    # we use `0` instead of `empty(uint256)` as return value.
    return 0 if (x == empty(uint256)) else unsafe_add(unsafe_div(x - 1, y), 1)


@internal
@pure
def _signum(x: int256) -> int256:
    """
    @dev Returns the indication of the sign of a 32-byte signed integer.
    @notice The function returns `-1` if `x < 0`, `0` if `x == 0`, and `1`
            if `x > 0`. For more details on finding the sign of a signed
            integer, please refer to:
            https://graphics.stanford.edu/~seander/bithacks.html#CopyIntegerSign.
    @param x The 32-byte signed integer variable.
    @return int256 The 32-byte sign indication (`1`, `0`, or `-1`) of `x`.
    """
    return unsafe_sub(convert((x > empty(int256)), int256), convert((x < empty(int256)), int256))


@internal
@pure
def _mul_div(x: uint256, y: uint256, denominator: uint256, roundup: bool) -> uint256:
    """
    @dev Calculates "(x * y) / denominator" in 512-bit precision,
         following the selected rounding direction.
    @notice The implementation is inspired by Remco Bloemen's
            implementation under the MIT license here:
            https://xn--2-umb.com/21/muldiv.
            Furthermore, the rounding direction design pattern is
            inspired by OpenZeppelin's implementation here:
            https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/utils/math/Math.sol.
    @param x The 32-byte multiplicand.
    @param y The 32-byte multiplier.
    @param denominator The 32-byte divisor.
    @param roundup The Boolean variable that specifies whether
           to round up or not. The default `False` is round down.
    @return uint256 The 32-byte calculation result.
    """
    # Handle division by zero.
    assert denominator != empty(uint256), "math: mul_div division by zero"

    # 512-bit multiplication "[prod1 prod0] = x * y".
    # Compute the product "mod 2**256" and "mod 2**256 - 1".
    # Then use the Chinese Remainder theorem to reconstruct
    # the 512-bit result. The result is stored in two 256-bit
    # variables, where: "product = prod1 * 2**256 + prod0".
    mm: uint256 = uint256_mulmod(x, y, max_value(uint256))
    # The least significant 256 bits of the product.
    prod0: uint256 = unsafe_mul(x, y)
    # The most significant 256 bits of the product.
    prod1: uint256 = empty(uint256)

    if mm < prod0:
        prod1 = unsafe_sub(unsafe_sub(mm, prod0), 1)
    else:
        prod1 = unsafe_sub(mm, prod0)

    # Handling of non-overflow cases, 256 by 256 division.
    if prod1 == empty(uint256):
        if roundup and uint256_mulmod(x, y, denominator) != empty(uint256):
            # Calculate "ceil((x * y) / denominator)". The following
            # line cannot overflow because we have the previous check
            # "(x * y) % denominator != 0", which accordingly rules out
            # the possibility of "x * y = 2**256 - 1" and `denominator == 1`.
            return unsafe_add(unsafe_div(prod0, denominator), 1)

        return unsafe_div(prod0, denominator)

    # Ensure that the result is less than "2**256". Also,
    # prevents that `denominator == 0`.
    assert denominator > prod1, "math: mul_div overflow"

    #######################
    # 512 by 256 Division #
    #######################

    # Make division exact by subtracting the remainder
    # from "[prod1 prod0]". First, compute remainder using
    # the `uint256_mulmod` operation.
    remainder: uint256 = uint256_mulmod(x, y, denominator)

    # Second, subtract the 256-bit number from the 512-bit
    # number.
    if remainder > prod0:
        prod1 = unsafe_sub(prod1, 1)
    prod0 = unsafe_sub(prod0, remainder)

    # Factor powers of two out of the denominator and calculate
    # the largest power of two divisor of denominator. Always `>= 1`,
    # unless the denominator is zero (which is prevented above),
    # in which case `twos` is zero. For more details, please refer to:
    # https://cs.stackexchange.com/q/138556.
    twos: uint256 = unsafe_sub(empty(uint256), denominator) & denominator
    # Divide denominator by `twos`.
    denominator_div: uint256 = unsafe_div(denominator, twos)
    # Divide "[prod1 prod0]" by `twos`.
    prod0 = unsafe_div(prod0, twos)
    # Flip `twos` such that it is "2**256 / twos". If `twos` is zero,
    # it becomes one.
    twos = unsafe_add(unsafe_div(unsafe_sub(empty(uint256), twos), twos), 1)

    # Shift bits from `prod1` to `prod0`.
    prod0 |= unsafe_mul(prod1, twos)

    # Invert the denominator "mod 2**256". Since the denominator is
    # now an odd number, it has an inverse modulo "2**256", so we have:
    # "denominator * inverse = 1 mod 2**256". Calculate the inverse by
    # starting with a seed that is correct for four bits. That is,
    # "denominator * inverse = 1 mod 2**4".
    inverse: uint256 = unsafe_mul(3, denominator_div) ^ 2

    # Use Newton-Raphson iteration to improve accuracy. Thanks to Hensel's
    # lifting lemma, this also works in modular arithmetic by doubling the
    # correct bits in each step.
    inverse = unsafe_mul(inverse, unsafe_sub(2, unsafe_mul(denominator_div, inverse))) # Inverse "mod 2**8".
    inverse = unsafe_mul(inverse, unsafe_sub(2, unsafe_mul(denominator_div, inverse))) # Inverse "mod 2**16".
    inverse = unsafe_mul(inverse, unsafe_sub(2, unsafe_mul(denominator_div, inverse))) # Inverse "mod 2**32".
    inverse = unsafe_mul(inverse, unsafe_sub(2, unsafe_mul(denominator_div, inverse))) # Inverse "mod 2**64".
    inverse = unsafe_mul(inverse, unsafe_sub(2, unsafe_mul(denominator_div, inverse))) # Inverse "mod 2**128".
    inverse = unsafe_mul(inverse, unsafe_sub(2, unsafe_mul(denominator_div, inverse))) # Inverse "mod 2**256".

    # Since the division is now exact, we can divide by multiplying
    # with the modular inverse of the denominator. This returns the
    # correct result modulo "2**256". Since the preconditions guarantee
    # that the result is less than "2**256", this is the final result.
    # We do not need to calculate the high bits of the result and
    # `prod1` is no longer necessary.
    result: uint256 = unsafe_mul(prod0, inverse)

    if roundup and uint256_mulmod(x, y, denominator) != empty(uint256):
        # Calculate "ceil((x * y) / denominator)". The following
        # line uses intentionally checked arithmetic to prevent
        # a theoretically possible overflow.
        result += 1

    return result


@internal
@pure
def _log2(x: uint256, roundup: bool) -> uint256:
    """
    @dev Returns the log in base 2 of `x`, following the selected
         rounding direction.
    @notice Note that it returns `0` if given `0`. The implementation
            is inspired by OpenZeppelin's implementation here:
            https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/utils/math/Math.sol.
    @param x The 32-byte variable.
    @param roundup The Boolean variable that specifies whether
           to round up or not. The default `False` is round down.
    @return uint256 The 32-byte calculation result.
    """
    # For the special case `x == 0`, we already return `0` here in order
    # not to iterate through the remaining code.
    if x == empty(uint256):
        return empty(uint256)

    value: uint256 = x
    result: uint256 = empty(uint256)

    # The following lines cannot overflow because we have the well-known
    # decay behaviour of `log2(max_value(uint256)) < max_value(uint256)`.
    if x >> 128 != empty(uint256):
        x >>= 128
        result = 128
    if x >> 64 != empty(uint256):
        x >>= 64
        result = unsafe_add(result, 64)
    if x >> 32 != empty(uint256):
        x >>= 32
        result = unsafe_add(result, 32)
    if x >> 16 != empty(uint256):
        x >>= 16
        result = unsafe_add(result, 16)
    if x >> 8 != empty(uint256):
        x >>= 8
        result = unsafe_add(result, 8)
    if x >> 4 != empty(uint256):
        x >>= 4
        result = unsafe_add(result, 4)
    if x >> 2 != empty(uint256):
        x >>= 2
        result = unsafe_add(result, 2)
    if x >> 1 != empty(uint256):
        result = unsafe_add(result, 1)

    if roundup and (1 << result) < value:
        result = unsafe_add(result, 1)

    return result


@internal
@pure
def _log10(x: uint256, roundup: bool) -> uint256:
    """
    @dev Returns the log in base 10 of `x`, following the selected
         rounding direction.
    @notice Note that it returns `0` if given `0`. The implementation
            is inspired by OpenZeppelin's implementation here:
            https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/utils/math/Math.sol.
    @param x The 32-byte variable.
    @param roundup The Boolean variable that specifies whether
           to round up or not. The default `False` is round down.
    @return uint256 The 32-byte calculation result.
    """
    # For the special case `x == 0`, we already return `0` here in order
    # not to iterate through the remaining code.
    if x == empty(uint256):
        return empty(uint256)

    value: uint256 = x
    result: uint256 = empty(uint256)

    # The following lines cannot overflow because we have the well-known
    # decay behaviour of `log10(max_value(uint256)) < max_value(uint256)`.
    if x >= 10 ** 64:
        x = unsafe_div(x, 10 ** 64)
        result = 64
    if x >= 10 ** 32:
        x = unsafe_div(x, 10 ** 32)
        result = unsafe_add(result, 32)
    if x >= 10 ** 16:
        x = unsafe_div(x, 10 ** 16)
        result = unsafe_add(result, 16)
    if x >= 10 ** 8:
        x = unsafe_div(x, 10 ** 8)
        result = unsafe_add(result, 8)
    if x >= 10 ** 4:
        x = unsafe_div(x, 10 ** 4)
        result = unsafe_add(result, 4)
    if x >= 10 ** 2:
        x = unsafe_div(x, 10 ** 2)
        result = unsafe_add(result, 2)
    if x >= 10:
        result = unsafe_add(result, 1)

    if roundup and (10 ** result) < value:
        result = unsafe_add(result, 1)

    return result


@internal
@pure
def _log256(x: uint256, roundup: bool) -> uint256:
    """
    @dev Returns the log in base 256 of `x`, following the selected
         rounding direction.
    @notice Note that it returns `0` if given `0`. Also, adding one to the
            rounded down result gives the number of pairs of hex symbols
            needed to represent `x` as a hex string. The implementation is
            inspired by OpenZeppelin's implementation here:
            https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/utils/math/Math.sol.
    @param x The 32-byte variable.
    @param roundup The Boolean variable that specifies whether
           to round up or not. The default `False` is round down.
    @return uint256 The 32-byte calculation result.
    """
    # For the special case `x == 0`, we already return `0` here in order
    # not to iterate through the remaining code.
    if x == empty(uint256):
        return empty(uint256)

    value: uint256 = x
    result: uint256 = empty(uint256)

    # The following lines cannot overflow because we have the well-known
    # decay behaviour of `log256(max_value(uint256)) < max_value(uint256)`.
    if x >> 128 != empty(uint256):
        x >>= 128
        result = 16
    if x >> 64 != empty(uint256):
        x >>= 64
        result = unsafe_add(result, 8)
    if x >> 32 != empty(uint256):
        x >>= 32
        result = unsafe_add(result, 4)
    if x >> 16 != empty(uint256):
        x >>= 16
        result = unsafe_add(result, 2)
    if x >> 8 != empty(uint256):
        result = unsafe_add(result, 1)

    if roundup and (1 << (result << 3)) < value:
        result = unsafe_add(result, 1)

    return result


@internal
@pure
def _wad_ln(x: int256) -> int256:
    """
    @dev Calculates the natural logarithm of a signed integer with a
         precision of 1e18.
    @notice Note that it returns `0` if given `0`. Furthermore, this function
            consumes about 1,400 to 1,650 gas units depending on the value
            of `x`. The implementation is inspired by Remco Bloemen's
            implementation under the MIT license here:
            https://xn--2-umb.com/22/exp-ln.
    @param x The 32-byte variable.
    @return int256 The 32-byte calculation result.
    """
    assert x >= empty(int256), "math: wad_ln undefined"

    # For the special case `x == 0`, we already return `0` here in order
    # not to iterate through the remaining code.
    if x == empty(int256):
        return empty(int256)

    # We want to convert `x` from "10**18" fixed point to "2**96"
    # fixed point. We do this by multiplying by "2**96 / 10**18".
    # But since "ln(x * C) = ln(x) + ln(C)" holds, we can just do
    # nothing here and add "ln(2**96 / 10**18)" at the end.

    # Reduce the range of `x` to "(1, 2) * 2**96".
    # Also remember that "ln(2**k * x) = k * ln(2) + ln(x)" holds.
    k: int256 = unsafe_sub(convert(self._log2(convert(x, uint256), False), int256), 96)
    # Note that to circumvent Vyper's safecast feature for the potentially
    # negative expression `x <<= uint256(159 - k)`, we first convert the
    # expression `x <<= uint256(159 - k)` to `bytes32` and subsequently
    # to `uint256`. Remember that the EVM default behaviour is to use two's
    # complement representation to handle signed integers.
    x = convert(convert(convert(x << convert(unsafe_sub(159, k), uint256), bytes32), uint256) >> 159, int256)

    # Evaluate using a "(8, 8)"-term rational approximation. Since `p` is monic,
    # we will multiply by a scaling factor later.
    p: int256 = unsafe_add(
        unsafe_mul(unsafe_add(x, 3_273_285_459_638_523_848_632_254_066_296), x) >> 96,
        24_828_157_081_833_163_892_658_089_445_524,
    )
    p = unsafe_add(unsafe_mul(p, x) >> 96, 43_456_485_725_739_037_958_740_375_743_393)
    p = unsafe_sub(unsafe_mul(p, x) >> 96, 11_111_509_109_440_967_052_023_855_526_967)
    p = unsafe_sub(unsafe_mul(p, x) >> 96, 45_023_709_667_254_063_763_336_534_515_857)
    p = unsafe_sub(unsafe_mul(p, x) >> 96, 14_706_773_417_378_608_786_704_636_184_526)
    p = unsafe_sub(unsafe_mul(p, x), 795_164_235_651_350_426_258_249_787_498 << 96)

    # We leave `p` in the "2**192" base so that we do not have to scale it up
    # again for the division. Note that `q` is monic by convention.
    q: int256 = unsafe_add(
        unsafe_mul(unsafe_add(x, 5_573_035_233_440_673_466_300_451_813_936), x) >> 96,
        71_694_874_799_317_883_764_090_561_454_958,
    )
    q = unsafe_add(unsafe_mul(q, x) >> 96, 283_447_036_172_924_575_727_196_451_306_956)
    q = unsafe_add(unsafe_mul(q, x) >> 96, 401_686_690_394_027_663_651_624_208_769_553)
    q = unsafe_add(unsafe_mul(q, x) >> 96, 204_048_457_590_392_012_362_485_061_816_622)
    q = unsafe_add(unsafe_mul(q, x) >> 96, 31_853_899_698_501_571_402_653_359_427_138)
    q = unsafe_add(unsafe_mul(q, x) >> 96, 909_429_971_244_387_300_277_376_558_375)

    # It is known that the polynomial `q` has no zeros in the domain.
    # No scaling is required, as `p` is already "2**96" too large. Also,
    # `r` is in the range "(0, 0.125) * 2**96" after the division.
    r: int256 = unsafe_div(p, q)

    # To finalise the calculation, we have to proceed with the following steps:
    #   - multiply by the scaling factor "s = 5.549...",
    #   - add "ln(2**96 / 10**18)",
    #   - add "k * ln(2)", and
    #   - multiply by "10**18 / 2**96 = 5**18 >> 78".
    # In order to perform the most gas-efficient calculation, we carry out all
    # these steps in one expression.
    return (
        unsafe_add(
            unsafe_add(
                unsafe_mul(r, 1_677_202_110_996_718_588_342_820_967_067_443_963_516_166),
                unsafe_mul(
                    k, 16_597_577_552_685_614_221_487_285_958_193_947_469_193_820_559_219_878_177_908_093_499_208_371
                ),
            ),
            600_920_179_829_731_861_736_702_779_321_621_459_595_472_258_049_074_101_567_377_883_020_018_308,
        )
        >> 174
    )


@internal
@pure
def _wad_exp(x: int256) -> int256:
    """
    @dev Calculates the natural exponential function of a signed integer with
         a precision of 1e18.
    @notice Note that this function consumes about 810 gas units. The implementation
            is inspired by Remco Bloemen's implementation under the MIT license here:
            https://xn--2-umb.com/22/exp-ln.
    @param x The 32-byte variable.
    @return int256 The 32-byte calculation result.
    """
    # If the result is `< 1`, we return zero. This happens when we have the following:
    # "x <= (log(1e-18) * 1e18) ~ -4.15e19".
    if x <= -41_446_531_673_892_822_313:
        return empty(int256)

    # When the result is "> (2**255 - 1) / 1e18" we cannot represent it as a signed integer.
    # This happens when "x >= floor(log((2**255 - 1) / 1e18) * 1e18) ~ 135".
    assert x < 135_305_999_368_893_231_589, "math: wad_exp overflow"

    # `x` is now in the range "(-42, 136) * 1e18". Convert to "(-42, 136) * 2**96" for higher
    # intermediate precision and a binary base. This base conversion is a multiplication with
    # "1e18 / 2**96 = 5**18 / 2**78".
    x = unsafe_div(x << 78, 5 ** 18)

    # Reduce the range of `x` to "(-½ ln 2, ½ ln 2) * 2**96" by factoring out powers of two
    # so that "exp(x) = exp(x') * 2**k", where `k` is a signer integer. Solving this gives
    # "k = round(x / log(2))" and "x' = x - k * log(2)". Thus, `k` is in the range "[-61, 195]".
    k: int256 = unsafe_add(unsafe_div(x << 96, 54_916_777_467_707_473_351_141_471_128), 2 ** 95) >> 96
    x = unsafe_sub(x, unsafe_mul(k, 54_916_777_467_707_473_351_141_471_128))

    # Evaluate using a "(6, 7)"-term rational approximation. Since `p` is monic,
    # we will multiply by a scaling factor later.
    y: int256 = unsafe_add(
        unsafe_mul(unsafe_add(x, 1_346_386_616_545_796_478_920_950_773_328), x) >> 96,
        57_155_421_227_552_351_082_224_309_758_442,
    )
    p: int256 = unsafe_add(
        unsafe_mul(
            unsafe_add(
                unsafe_mul(unsafe_sub(unsafe_add(y, x), 94_201_549_194_550_492_254_356_042_504_812), y) >> 96,
                28_719_021_644_029_726_153_956_944_680_412_240,
            ),
            x,
        ),
        4_385_272_521_454_847_904_659_076_985_693_276 << 96,
    )

    # We leave `p` in the "2**192" base so that we do not have to scale it up
    # again for the division.
    q: int256 = unsafe_add(
        unsafe_mul(unsafe_sub(x, 2_855_989_394_907_223_263_936_484_059_900), x) >> 96,
        50_020_603_652_535_783_019_961_831_881_945,
    )
    q = unsafe_sub(unsafe_mul(q, x) >> 96, 533_845_033_583_426_703_283_633_433_725_380)
    q = unsafe_add(unsafe_mul(q, x) >> 96, 3_604_857_256_930_695_427_073_651_918_091_429)
    q = unsafe_sub(unsafe_mul(q, x) >> 96, 14_423_608_567_350_463_180_887_372_962_807_573)
    q = unsafe_add(unsafe_mul(q, x) >> 96, 26_449_188_498_355_588_339_934_803_723_976_023)

    # The polynomial `q` has no zeros in the range because all its roots are complex.
    # No scaling is required, as `p` is already "2**96" too large. Also,
    # `r` is in the range "(0.09, 0.25) * 2**96" after the division.
    r: int256 = unsafe_div(p, q)

    # To finalise the calculation, we have to multiply `r` by:
    #   - the scale factor "s = ~6.031367120",
    #   - the factor "2**k" from the range reduction, and
    #   - the factor "1e18 / 2**96" for the base conversion.
    # We do this all at once, with an intermediate result in "2**213" base,
    # so that the final right shift always gives a positive value.

    # Note that to circumvent Vyper's safecast feature for the potentially
    # negative parameter value `r`, we first convert `r` to `bytes32` and
    # subsequently to `uint256`. Remember that the EVM default behaviour is
    # to use two's complement representation to handle signed integers.
    return convert(
        unsafe_mul(
            convert(convert(r, bytes32), uint256), 3_822_833_074_963_236_453_042_738_258_902_158_003_155_416_615_667
        )
        >> convert(unsafe_sub(195, k), uint256),
        int256,
    )


@internal
@pure
def _cbrt(x: uint256, roundup: bool) -> uint256:
    """
    @dev Calculates the cube root of an unsigned integer.
    @notice Note that this function consumes about 1,600 to 1,800 gas units
            depending on the value of `x` and `roundup`. The implementation is
            inspired by Curve Finance's implementation under the MIT license here:
            https://github.com/curvefi/tricrypto-ng/blob/main/contracts/main/CurveCryptoMathOptimized3.vy.
    @param x The 32-byte variable from which the cube root is calculated.
    @param roundup The Boolean variable that specifies whether
           to round up or not. The default `False` is round down.
    @return The 32-byte cube root of `x`.
    """
    # For the special case `x == 0`, we already return `0` here in order
    # not to iterate through the remaining code.
    if x == empty(uint256):
        return empty(uint256)

    y: uint256 = unsafe_div(self._wad_cbrt(x), 10 ** 12)

    if roundup and unsafe_mul(unsafe_mul(y, y), y) != x:
        y = unsafe_add(y, 1)

    return y


@internal
@pure
def _wad_cbrt(x: uint256) -> uint256:
    """
    @dev Calculates the cube root of an unsigned integer with a precision
         of 1e18.
    @notice Note that this function consumes about 1,500 to 1,700 gas units
            depending on the value of `x`. The implementation is inspired
            by Curve Finance's implementation under the MIT license here:
            https://github.com/curvefi/tricrypto-ng/blob/main/contracts/main/CurveCryptoMathOptimized3.vy.
    @param x The 32-byte variable from which the cube root is calculated.
    @return The 32-byte cubic root of `x` with a precision of 1e18.
    """
    # For the special case `x == 0`, we already return `0` here in order
    # not to iterate through the remaining code.
    if x == empty(uint256):
        return empty(uint256)

    # Since this cube root is for numbers with base 1e18, we have to scale
    # the input by 1e36 to increase the precision. This leads to an overflow
    # for very large numbers. So we conditionally sacrifice precision.
    value: uint256 = empty(uint256)
    if x >= unsafe_mul(unsafe_div(max_value(uint256), 10 ** 36), 10 ** 18):
        value = x
    elif x >= unsafe_div(max_value(uint256), 10 ** 36):
        value = unsafe_mul(x, 10 ** 18)
    else:
        value = unsafe_mul(x, 10 ** 36)

    # Compute the binary logarithm of `value`.
    log2x: uint256 = self._log2(value, False)

    # If we divide log2x by 3, the remainder is "log2x % 3". So if we simply
    # multiply "2**(log2x/3)" and discard the remainder to calculate our guess,
    # the Newton-Raphson method takes more iterations to converge to a solution
    # because it lacks this precision. A few more calculations now in order to
    # do fewer calculations later:
    #   - "pow = log2(x) // 3" (the operator `//` means integer division),
    #   - "remainder = log2(x) % 3",
    #   - "initial_guess = 2**pow * cbrt(2)**remainder".
    # Now substituting "2 = 1.26 ≈ 1,260 / 1,000", we get:
    #   - "initial_guess = 2**pow * 1,260**remainder // 1,000**remainder".
    remainder: uint256 = log2x % 3
    y: uint256 = unsafe_div(
        unsafe_mul(pow_mod256(2, unsafe_div(log2x, 3)), pow_mod256(1_260, remainder)), pow_mod256(1_000, remainder)
    )

    # Since we have chosen good initial values for the cube roots, 7 Newton-Raphson
    # iterations are just sufficient. 6 iterations would lead to non-convergences,
    # and 8 would be one iteration too many. Without initial values, the iteration
    # number can be up to 20 or more. The iterations are unrolled. This reduces the
    # gas cost, but requires more bytecode.
    y = unsafe_div(unsafe_add(unsafe_mul(2, y), unsafe_div(value, unsafe_mul(y, y))), 3)
    y = unsafe_div(unsafe_add(unsafe_mul(2, y), unsafe_div(value, unsafe_mul(y, y))), 3)
    y = unsafe_div(unsafe_add(unsafe_mul(2, y), unsafe_div(value, unsafe_mul(y, y))), 3)
    y = unsafe_div(unsafe_add(unsafe_mul(2, y), unsafe_div(value, unsafe_mul(y, y))), 3)
    y = unsafe_div(unsafe_add(unsafe_mul(2, y), unsafe_div(value, unsafe_mul(y, y))), 3)
    y = unsafe_div(unsafe_add(unsafe_mul(2, y), unsafe_div(value, unsafe_mul(y, y))), 3)
    y = unsafe_div(unsafe_add(unsafe_mul(2, y), unsafe_div(value, unsafe_mul(y, y))), 3)

    # Since we scaled up, we have to scale down accordingly.
    if x >= unsafe_mul(unsafe_div(max_value(uint256), 10 ** 36), 10 ** 18):
        return unsafe_mul(y, 10 ** 12)
    elif x >= unsafe_div(max_value(uint256), 10 ** 36):
        return unsafe_mul(y, 10 ** 6)

    return y


// ---- contracts/dao/YB.vy ----
# @version 0.4.3
"""
@title YBToken
@author Yield Basis
@license GNU Affero General Public License v3.0
@notice YB Token
"""

from snekmate.auth import ownable
from snekmate.tokens import erc20
from snekmate.utils import math


initializes: ownable
initializes: erc20[ownable := ownable]


exports: (
    erc20.IERC20,
    erc20.IERC20Detailed,
    erc20.mint,
    erc20.is_minter,
    erc20.set_minter,
    erc20.transfer_ownership,
    ownable.owner
)


reserve: public(uint256)  # Reserve of tokens to be minted
last_minted: public(uint256)  # Last time minting has happened
max_mint_rate: public(immutable(uint256))  # Ceiling of the mint rate


@deploy
def __init__(reserve: uint256, max_rate: uint256):
    """
    @param reserve Amount of YB tokens to emit over infinite time
    @param max_rate Maximum emission rate in tokens per second (reached when rate_factor=1.0)
    """
    ownable.__init__()
    erc20.__init__("Yield Basis", "YB", 18, "Just say no", "to EIP712")
    # Ownership is now with msg.sender
    # The setup includes:
    # * Minting preallocations
    # * set_minter(GaugeController, True)
    # * renounce_ownership(deployer) - will also unset the minter

    self.reserve = reserve
    max_mint_rate = max_rate * 10**18 // reserve


@internal
@view
def _emissions(t: uint256, rate_factor: uint256) -> uint256:
    assert rate_factor <= 10**18
    last_minted: uint256 = self.last_minted
    if last_minted == 0 or t <= last_minted:
        return 0
    else:
        dt: int256 = convert(t - last_minted, int256)
        rate_36: int256 = convert(max_mint_rate * rate_factor, int256)
        reserve: int256 = convert(self.reserve, int256)
        return convert(
            reserve * (10**18 - math._wad_exp(-dt * rate_36 // 10**18)) // 10**18,
            uint256)


@external
@view
def preview_emissions(t: uint256, rate_factor: uint256) -> uint256:
    """
    @notice Calculate the amount of emissions to be released by the time t
    @param t Time for which the emissions should be calculated
    @param rate_factor Average rate factor from 0.0 (0) to 1.0 (1e18)
    """
    return self._emissions(t, rate_factor)


@external
def start_emissions():
    """
    @notice Start token emissions. Ownership must be renounced no earlier than emissions are started
    """
    ownable._check_owner()
    if self.last_minted == 0:
        self.last_minted = block.timestamp


@external
def renounce_ownership():
    """
    @notice Method for deployer to renounce ownership of the token. After this only GaugeController can mint
    """
    ownable._check_owner()
    # Force-strt emissions when renouncing ownership
    if self.last_minted == 0:
        self.last_minted = block.timestamp
    erc20.is_minter[msg.sender] = False
    log erc20.RoleMinterChanged(minter=msg.sender, status=False)
    ownable._transfer_ownership(empty(address))


@external
def emit(owner: address, rate_factor: uint256) -> uint256:
    """
    @dev Creates `amount` tokens and assigns them to `owner`.
    @notice Only authorised minters can access this function.
            Note that `owner` cannot be the zero address.
    @param owner The 20-byte owner address.
    @param rate_factor What percentage of inflation to mint (100% = 10**18)
    """
    assert erc20.is_minter[msg.sender], "erc20: access is denied"

    amount: uint256 = 0

    if self.last_minted > 0:
        amount = self._emissions(block.timestamp, rate_factor)
        self.reserve -= amount
        self.last_minted = block.timestamp
        erc20._mint(owner, amount)

    return amount
