// ---- src/MaseerOne.sol ----
// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2025 Maseer LTD
//
// This file is subject to the Business Source License 1.1.
// You may not use this file except in compliance with the License.
//
// You may obtain a copy of the License at:
// https://github.com/Maseer-LTD/maseer-one/blob/master/LICENSE
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
pragma solidity ^0.8.28;

import {MaseerToken} from "./MaseerToken.sol";

interface Gem {
    function transfer(address usr, uint256 wad) external returns (bool);
    function transferFrom(address src, address dst, uint256 wad) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface Cop {
    function pass(address usr) external view returns (bool);
}

interface Pip {
    function read() external view returns (uint256);
}

interface Act {
    function mintable() external view returns (bool);
    function burnable() external view returns (bool);
    function cooldown() external view returns (uint256);
    function capacity() external view returns (uint256);
    function mintcost(uint256) external view returns (uint256);
    function burncost(uint256) external view returns (uint256);
    function terms() external view returns (string memory);
}

interface Adm {
    function issuer(address usr) external view returns (bool);
}

// ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
// :==============================================================:
// :==============================================================:
// :==============================================================:
// :==============================================================:
// :==============================================================:
// :============@@@@@@@@@@@=@@@@@@==@@@@@@========================:
// :===========@@.........@@@.....@@@....@========================:
// :===========@........@@@.....@@@....@@@========================:
// :===========@......@@@.....@@@.....@@@=========================:
// :===========@....@@@:....@@@.....@@@===========================:
// :===========@..:@@@....@@@-....@@@=============================:
// :===========@:@@@....@@@@....@@@===============================:
// :===========@@@....@@@@....@@@=================================:
// :===========@.....@@@....@@@===================================:
// :===========@...@@@....:@@@====================================:
// :===========@:@@@.....@@@====@@@@@@@@@@====@@@@@@@@@===========:
// :===========@@@.....@@@======@........@+==@@.......@===========:
// :===========@:....@@@========@........@@==@........@===========:
// :===========@...@@@==========@.........@=@@........@===========:
// :===========@.@@@============@.........@@@.........@===========:
// :===========@@@==============@..........@..........@===========:
// :============================@..........#..........@===========:
// :============================@.....................@===========:
// :============================@.....................@===========:
// :============================@......@.......@......@===========:
// :============================@......@@......@......@===========:
// :============================@......@@.....@@......@===========:
// :============================*@@@@@@*#@@@@@#*@@@@@@*===========:
// :==============================================================:
// :==============================================================:
// :==============================================================:
// :==============================================================:
// :==============================================================:
// ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
contract MaseerOne is MaseerToken {

    address immutable public gem;  // Purchase token
    address immutable public pip;  // Oracle price feed
    address immutable public act;  // Market timing feed
    address immutable public adm;  // Issuer control
    address immutable public cop;  // Compliance feed
    address immutable public flo;  // Output conduit

    uint256                         public totalPending;
    uint256                         public redemptionCount;
    mapping (uint256 => Redemption) public redemptions;

    struct Redemption {
        uint256 amount;
        address redeemer;
        uint96  date;
    }

    event ContractCreated(
        address indexed creator,
        uint256 indexed price,
        uint256 indexed amount
    );
    event ContractRedemption(
        uint256 indexed id,
        uint256 indexed date,
        address indexed redeemer,
        uint256         amount
    );
    event ClaimProcessed(
        uint256 indexed id,
        address indexed claimer,
        uint256 indexed amount
    );
    event Settled(
        address indexed conduit,
        uint256 indexed amount
    );
    event Issued(
        address indexed issuer,
        uint256 indexed amount
    );
    event Smelted(
        address indexed smelter,
        uint256 indexed amount
    );

    error NotAuthorized(address usr);
    error TransferToContract();
    error TransferToZeroAddress();
    error TransferFailed();
    error MarketClosed();
    error InvalidPrice();
    error ExceedsCap();
    error ClaimableAfter(uint256 time);
    error NoPendingClaim();
    error DustThreshold(uint256 min);

    constructor(
        address gem_,
        address pip_,
        address act_,
        address adm_,
        address cop_,
        address flo_,
        string memory name_,
        string memory symbol_
    ) MaseerToken(name_, symbol_) {
        gem = gem_;
        pip = pip_;
        act = act_;
        adm = adm_;
        cop = cop_;
        flo = flo_;
    }

    modifier pass(address usr_) {
        if (!_canPass(usr_)) revert NotAuthorized(usr_);
        _;
    }

    modifier mintlive() {
        if (!mintable()) revert MarketClosed();
        _;
    }

    modifier burnlive() {
        if (!burnable()) revert MarketClosed();
        _;
    }

    modifier issuer() {
        if (!Adm(adm).issuer(msg.sender)) revert NotAuthorized(msg.sender);
        _;
    }

    function mint(uint256 amt) external mintlive pass(msg.sender) returns (uint256 _out) {
        // Oracle price check
        uint256 _unit = _read();

        // Revert if the price is zero
        if (_unit == 0) revert InvalidPrice();

        // Adjust the price for minting
        _unit = _mintcost(_unit);

        // Assert minimum purchase amount of one unit to avoid dust
        if (amt < _unit) revert DustThreshold(_unit);

        // Calculate the mint amount
        _out = _wdiv(amt, _unit);

        // Revert if the total supply after mint exceeds the cap
        if (totalSupply + _out > _capacity()) revert ExceedsCap();

        // Transfer tokens in
        _safeTransferFrom(gem, msg.sender, address(this), amt);

        // Mint the tokens
        _mint(msg.sender, _out);

        // Emit contract event
        emit ContractCreated(msg.sender, _unit, _out);
    }

    function redeem(uint256 amt) external burnlive pass(msg.sender) returns (uint256 _id) {
        // Assert minimum redemption amount of one token to avoid dust
        if (amt < WAD) revert DustThreshold(WAD);

        // Oracle price check
        uint256 _unit = _read();

        // Revert if the price is zero
        if (_unit == 0) revert InvalidPrice();

        // Adjust the price for redemption
        _unit = _burncost(_unit);

        // Calculate the redemption amount
        uint256 _claim = _wmul(amt, _unit);

        // Add to the total pending redemptions
        totalPending += _claim;

        // Assign a new redemption ID
        _id = redemptionCount++;

        // Calculate the redemption date
        uint96 _time = uint96(block.timestamp + _cooldown());

        // Store the redemption
        redemptions[_id] = Redemption({
            amount:   _claim,
            redeemer: msg.sender,
            date:     _time
        });

        // Burn the tokens
        _burn(msg.sender, amt);

        // Emit contract event
        emit ContractRedemption(_id, _time, msg.sender, _claim);
    }

    function exit(uint256 id) external pass(msg.sender) returns (uint256 _out) {
        Redemption storage _redemption = redemptions[id];

        uint256 _time = _redemption.date;

        // Check if the claim is past the redemption period
        if (_time > block.timestamp) revert ClaimableAfter(_time);
        if (_time == 0) revert NoPendingClaim();

        uint256 _amt = _redemption.amount;
        uint256 _bal = _gemBalance();
        // User can claim the amount owed or current available balance
        _out = (_amt < _bal) ? _amt : _bal;

        // Decrement the total pending redemptions
        // Decrement the user's pending redemptions
        unchecked {
            totalPending -= _out;
            _redemption.amount -= _out;
        }

        // Transfer the tokens
        _safeTransfer(gem, _redemption.redeemer, _out);

        // Emit claim
        emit ClaimProcessed(id, _redemption.redeemer, _out);
    }

    function settle() external pass(msg.sender) returns (uint256 _out) {
        // Get the gem balance
        uint256 _bal = _gemBalance();
        uint256 _pnd = totalPending;

        // Return 0 if the balance is reserved for pending claims
        if (_bal <= _pnd) return 0;

        // Calculate the balance after pending redemptions
        unchecked {
            _out = _bal - _pnd;
        }

        // Send the remaining balance to the output conduit
        _safeTransfer(gem, flo, _out);

        // Emit settle
        emit Settled(flo, _out);
    }

    // Issuer function for minting assets or bridging
    function issue(uint256 amt) external issuer pass(msg.sender) {
        _mint(msg.sender, amt);

        emit Issued(msg.sender, amt);
    }

    // Issuer smelting function to burn for a specific user
    function smelt(address usr, uint256 amt) external issuer pass(msg.sender) {
        _burn(usr, amt);

        emit Smelted(usr, amt);
    }

    // User-level smelting function for burning tokens
    function smelt(uint256 amt) external pass(msg.sender) {
        _burn(msg.sender, amt);

        emit Smelted(msg.sender, amt);
    }

    // View functions

    function mintable() public view returns (bool) {
        return Act(act).mintable();
    }

    function burnable() public view returns (bool) {
        return Act(act).burnable();
    }

    function canPass(address usr) external view returns (bool) {
        return _canPass(usr);
    }

    function cooldown() external view returns (uint256) {
        return _cooldown();
    }

    function navprice() external view returns (uint256) {
        return _read();
    }

    function mintcost() external view returns (uint256) {
        return _mintcost(_read());
    }

    function burncost() external view returns (uint256) {
        return _burncost(_read());
    }

    function capacity() external view returns (uint256) {
        return _capacity();
    }

    function terms() external view returns (string memory) {
        return Act(act).terms();
    }

    function redemptionAddr(uint256 id) external view returns (address) {
        return redemptions[id].redeemer;
    }

    function redemptionDate(uint256 id) external view returns (uint256) {
        return redemptions[id].date;
    }

    function redemptionAmount(uint256 id) external view returns (uint256) {
        return redemptions[id].amount;
    }

    function unsettled() external view returns (uint256) {
        uint256 _bal = _gemBalance();
        return (_bal < totalPending) ? 0 : _bal - totalPending;
    }

    function obligated() external view returns (uint256) {
        uint256 _bal = _gemBalance();
        return (_bal > totalPending) ? 0 : totalPending - _bal;
    }

    // Token overrides for compliance

    function approve(address usr) public override pass(msg.sender) pass(usr) returns (bool) {
        return super.approve(usr);
    }

    function approve(address usr, uint256 wad) public override pass(msg.sender) pass(usr) returns (bool) {
        return super.approve(usr, wad);
    }

    function transfer(address dst, uint256 wad) public override pass(msg.sender) pass(dst) returns (bool) {
        if (dst == address(this)) revert TransferToContract();
        return super.transfer(dst, wad);
    }

    function transferFrom(address src, address dst, uint256 wad) public override pass(msg.sender) pass(src) pass(dst) returns (bool) {
        if (dst == address(this)) revert TransferToContract();
        return super.transferFrom(src, dst, wad);
    }

    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8   v,
        bytes32 r,
        bytes32 s
    ) public override pass(msg.sender) pass(owner) pass(spender) {
        super.permit(owner, spender, value, deadline, v, r, s);
    }

    // Internal utility functions

    function _canPass(address _usr) internal view returns (bool) {
        return Cop(cop).pass(_usr);
    }

    function _cooldown() internal view returns (uint256) {
        return Act(act).cooldown();
    }

    function _mintcost(uint256 _price) internal view returns (uint256) {
        return Act(act).mintcost(_price);
    }

    function _burncost(uint256 _price) internal view returns (uint256) {
        return Act(act).burncost(_price);
    }

    function _capacity() internal view returns (uint256) {
        return Act(act).capacity();
    }

    function _read() internal view returns (uint256) {
        return Pip(pip).read();
    }

    function _gemBalance() internal view returns (uint256) {
        return Gem(gem).balanceOf(address(this));
    }

    function _wdiv(uint256 x, uint256 y) internal pure returns (uint256 z) {
        z = (x * WAD) / y;
    }

    function _wmul(uint256 x, uint256 y) internal pure returns (uint256 z) {
        z = (x * y) / WAD;
    }

    function _safeTransfer(address _token, address _to, uint256 _amt) internal {
        (bool success, bytes memory data) = _token.call(abi.encodeWithSelector(Gem.transfer.selector, _to, _amt));
        if (!success || (data.length > 0 && abi.decode(data, (bool)) == false)) revert TransferFailed();
    }

    function _safeTransferFrom(address _token, address _from, address _to, uint256 _amt) internal {
        (bool success, bytes memory data) = _token.call(abi.encodeWithSelector(Gem.transferFrom.selector, _from, _to, _amt));
        if (!success || (data.length > 0 && abi.decode(data, (bool)) == false)) revert TransferFailed();
    }
}


// ---- src/MaseerToken.sol ----
// SPDX-License-Identifier: BUSL-1.1
// Copyright (c) 2025 Maseer LTD
//
// This file is subject to the Business Source License 1.1.
// You may not use this file except in compliance with the License.
//
// You may obtain a copy of the License at:
// https://github.com/Maseer-LTD/maseer-one/blob/master/LICENSE
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
pragma solidity ^0.8.28;

abstract contract MaseerToken {

    // ERC-20
    uint256                                           public totalSupply;
    mapping (address => uint256)                      public balanceOf;
    mapping (address => mapping (address => uint256)) public allowance;
    string                                            public name;
    string                                            public symbol;
    uint8                                    constant public decimals = 18; // standard token precision.

    uint256                                  constant internal WAD = 1e18;

    // EIP-2612
    bytes32 immutable         internal INITIAL_DOMAIN_SEPARATOR;
    uint256 immutable         internal INITIAL_CHAIN_ID;
    mapping(address => uint256) public nonces;

    constructor(string memory name_, string memory symbol_) {
        name   = name_;
        symbol = symbol_;

        INITIAL_CHAIN_ID = block.chainid;
        INITIAL_DOMAIN_SEPARATOR = _computeDomainSeparator();
    }

    event Approval(address indexed src, address indexed usr, uint256 wad);
    event Transfer(address indexed src, address indexed dst, uint256 wad);

    error InvalidChain(uint256 expected, uint256 actual);
    error PermitDeadlineExpired(uint256 deadline, uint256 actual);
    error InvalidSigner(address recovered, address expected);

    function approve(address usr) public virtual returns (bool) {
        return approve(usr, type(uint256).max);
    }

    function approve(address usr, uint256 wad) public virtual returns (bool) {
        allowance[msg.sender][usr] = wad;

        emit Approval(msg.sender, usr, wad);

        return true;
    }

    function transfer(address dst, uint256 wad) public virtual returns (bool) {
        balanceOf[msg.sender] -= wad;

        // Cannot overflow because balance
        //   can't exceed totalSupply
        unchecked {
            balanceOf[dst] += wad;
        }

        emit Transfer(msg.sender, dst, wad);

        return true;
    }

    function transferFrom(address src, address dst, uint256 wad)
        public virtual
        returns (bool)
    {
        uint256 _allowance = allowance[src][msg.sender];
        if (_allowance != type(uint256).max) {
            allowance[src][msg.sender] = _allowance - wad;
        }

        balanceOf[src] -= wad;
        balanceOf[dst] += wad;

        emit Transfer(src, dst, wad);

        return true;
    }

    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8   v,
        bytes32 r,
        bytes32 s
    ) public virtual {
        if (deadline < block.timestamp) revert PermitDeadlineExpired(deadline, block.timestamp);

        // Unchecked because the owner's nonce is uint256 which cannot realistically overflow.
        unchecked {
            address recoveredAddress = ecrecover(
                keccak256(
                    abi.encodePacked(
                        "\x19\x01",
                        DOMAIN_SEPARATOR(),
                        keccak256(
                            abi.encode(
                                keccak256(
                                    "Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"
                                ),
                                owner,
                                spender,
                                value,
                                nonces[owner]++,
                                deadline
                            )
                        )
                    )
                ),
                v,
                r,
                s
            );

            if (recoveredAddress == address(0) || recoveredAddress != owner) revert InvalidSigner(recoveredAddress, owner);

            allowance[recoveredAddress][spender] = value;
        }

        emit Approval(owner, spender, value);
    }

    function _mint(address usr, uint256 wad) internal {
        totalSupply += wad;
        // Cannot overflow
        unchecked {
            balanceOf[usr] += wad;
        }
        emit Transfer(address(0), usr, wad);
    }

    function _burn(address usr, uint256 wad) internal {
        balanceOf[usr] -= wad;
        // Cannot overflow
        unchecked {
            totalSupply -= wad;
        }
        emit Transfer(usr, address(0), wad);
    }

    function DOMAIN_SEPARATOR() public view returns (bytes32) {
        return (block.chainid == INITIAL_CHAIN_ID) ? INITIAL_DOMAIN_SEPARATOR : _computeDomainSeparator();
    }

    function _computeDomainSeparator() internal view returns (bytes32) {
        return keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes(name)),
            keccak256(bytes("1")),
            block.chainid,
            address(this)
        ));
    }
}
