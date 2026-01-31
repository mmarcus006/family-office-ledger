"""Domain models for cryptocurrency and DeFi investments.

Provides comprehensive tracking for:
- Crypto wallets (hot, cold, exchange)
- Token positions with cost basis tracking
- DeFi positions (staking, lending, liquidity pools)
- NFT holdings
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from family_office_ledger.domain.value_objects import Money


def _utc_now() -> datetime:
    return datetime.now(UTC)


class WalletType(str, Enum):
    """Type of cryptocurrency wallet."""

    EXCHANGE = "exchange"  # Centralized exchange (Coinbase, Kraken, etc.)
    HOT_WALLET = "hot_wallet"  # Software wallet
    COLD_WALLET = "cold_wallet"  # Hardware wallet (Ledger, Trezor)
    CUSTODIAL = "custodial"  # Third-party custody
    MULTISIG = "multisig"  # Multi-signature wallet
    SMART_CONTRACT = "smart_contract"  # Contract-based (Gnosis Safe, etc.)


class BlockchainNetwork(str, Enum):
    """Blockchain network."""

    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"
    SOLANA = "solana"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    BASE = "base"
    AVALANCHE = "avalanche"
    BSC = "bsc"  # BNB Smart Chain
    COSMOS = "cosmos"
    CARDANO = "cardano"
    POLKADOT = "polkadot"
    NEAR = "near"
    APTOS = "aptos"
    SUI = "sui"


class TokenType(str, Enum):
    """Type of crypto token."""

    NATIVE = "native"  # Native chain token (ETH, SOL, etc.)
    ERC20 = "erc20"
    ERC721 = "erc721"  # NFT
    ERC1155 = "erc1155"  # Multi-token
    SPL = "spl"  # Solana
    BEP20 = "bep20"  # BSC
    WRAPPED = "wrapped"  # Wrapped token (WETH, WBTC)
    STABLECOIN = "stablecoin"
    GOVERNANCE = "governance"
    UTILITY = "utility"
    LP_TOKEN = "lp_token"  # Liquidity pool token


class DeFiPositionType(str, Enum):
    """Type of DeFi position."""

    STAKING = "staking"
    LENDING = "lending"
    BORROWING = "borrowing"
    LIQUIDITY_POOL = "liquidity_pool"
    YIELD_FARMING = "yield_farming"
    VAULT = "vault"
    LIQUID_STAKING = "liquid_staking"  # stETH, rETH, etc.
    RESTAKING = "restaking"  # EigenLayer, etc.
    OPTIONS = "options"
    PERPETUALS = "perpetuals"


class DeFiProtocol(str, Enum):
    """Major DeFi protocols."""

    AAVE = "aave"
    COMPOUND = "compound"
    UNISWAP = "uniswap"
    CURVE = "curve"
    MAKER = "maker"
    LIDO = "lido"
    ROCKET_POOL = "rocket_pool"
    EIGENLAYER = "eigenlayer"
    CONVEX = "convex"
    YEARN = "yearn"
    BALANCER = "balancer"
    SUSHISWAP = "sushiswap"
    PANCAKESWAP = "pancakeswap"
    GMX = "gmx"
    DYDX = "dydx"
    OTHER = "other"


class TransactionType(str, Enum):
    """Type of crypto transaction for tax purposes."""

    BUY = "buy"
    SELL = "sell"
    TRANSFER = "transfer"  # Between own wallets
    RECEIVE = "receive"  # From external
    SEND = "send"  # To external
    SWAP = "swap"
    STAKE = "stake"
    UNSTAKE = "unstake"
    CLAIM_REWARDS = "claim_rewards"
    DEPOSIT = "deposit"  # To protocol
    WITHDRAW = "withdraw"  # From protocol
    MINT = "mint"
    BURN = "burn"
    AIRDROP = "airdrop"
    FORK = "fork"
    GIFT_RECEIVED = "gift_received"
    GIFT_SENT = "gift_sent"
    INCOME = "income"  # Mining, staking rewards
    FEE = "fee"


@dataclass
class CryptoToken:
    """A cryptocurrency token definition."""

    symbol: str
    name: str
    network: BlockchainNetwork
    id: UUID = field(default_factory=uuid4)
    token_type: TokenType = TokenType.NATIVE
    contract_address: str | None = None
    decimals: int = 18
    coingecko_id: str | None = None  # For price feeds
    cmc_id: int | None = None  # CoinMarketCap ID
    is_stablecoin: bool = False
    pegged_to: str | None = None  # "USD", "ETH", etc.
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class CryptoWallet:
    """A cryptocurrency wallet."""

    name: str
    entity_id: UUID
    wallet_type: WalletType
    id: UUID = field(default_factory=uuid4)
    networks: list[BlockchainNetwork] = field(default_factory=list)

    # Addresses by network
    addresses: dict[str, str] = field(default_factory=dict)  # network -> address

    # Exchange-specific
    exchange_name: str | None = None
    exchange_account_id: str | None = None
    api_key_configured: bool = False

    # Hardware wallet
    hardware_type: str | None = None  # "ledger", "trezor", etc.
    hardware_serial: str | None = None

    # Tracking
    last_synced: datetime | None = None
    is_active: bool = True
    notes: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def get_address(self, network: BlockchainNetwork) -> str | None:
        """Get wallet address for a specific network."""
        return self.addresses.get(network.value)

    def set_address(self, network: BlockchainNetwork, address: str) -> None:
        """Set wallet address for a network."""
        self.addresses[network.value] = address
        if network not in self.networks:
            self.networks.append(network)


@dataclass
class CryptoPosition:
    """A cryptocurrency position (holding)."""

    wallet_id: UUID
    token_id: UUID
    quantity: Decimal
    id: UUID = field(default_factory=uuid4)
    cost_basis: Money = field(default_factory=lambda: Money(Decimal("0")))
    cost_basis_per_unit: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Current value (updated by market data service)
    current_price: Money | None = None
    current_value: Money | None = None
    price_updated_at: datetime | None = None

    # Tax lot tracking
    acquisition_date: date | None = None
    acquisition_transaction_id: UUID | None = None

    # For staked/locked positions
    is_locked: bool = False
    unlock_date: date | None = None
    staking_protocol: str | None = None

    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @property
    def unrealized_gain(self) -> Money | None:
        """Unrealized gain/loss."""
        if self.current_value is None:
            return None
        return Money(self.current_value.amount - self.cost_basis.amount)

    @property
    def unrealized_gain_percent(self) -> Decimal | None:
        """Unrealized gain/loss as percentage."""
        if self.current_value is None or self.cost_basis.amount == 0:
            return None
        return (
            (self.current_value.amount - self.cost_basis.amount)
            / self.cost_basis.amount
        )


@dataclass
class CryptoTaxLot:
    """A tax lot for crypto cost basis tracking.

    Crypto requires per-wallet tax lot tracking in many jurisdictions.
    """

    wallet_id: UUID
    token_id: UUID
    quantity: Decimal
    acquisition_date: date
    cost_basis: Money
    id: UUID = field(default_factory=uuid4)
    acquisition_type: TransactionType = TransactionType.BUY
    acquisition_transaction_hash: str | None = None
    fee_paid: Money = field(default_factory=lambda: Money(Decimal("0")))

    # Disposal tracking
    remaining_quantity: Decimal | None = None
    is_fully_disposed: bool = False

    # For income (staking, mining, airdrops)
    fair_market_value_at_receipt: Money | None = None
    income_reported: bool = False

    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity

    @property
    def cost_per_unit(self) -> Decimal:
        """Cost basis per unit including fees."""
        if self.quantity == 0:
            return Decimal("0")
        total_cost = self.cost_basis.amount + self.fee_paid.amount
        return total_cost / self.quantity

    def dispose(self, quantity: Decimal) -> tuple[Decimal, Money]:
        """Dispose of units from this lot.

        Args:
            quantity: Number of units to dispose

        Returns:
            Tuple of (quantity disposed, cost basis disposed)
        """
        if self.remaining_quantity is None or self.remaining_quantity <= 0:
            return Decimal("0"), Money(Decimal("0"))

        disposed = min(quantity, self.remaining_quantity)
        basis_disposed = self.cost_per_unit * disposed

        self.remaining_quantity -= disposed
        if self.remaining_quantity <= 0:
            self.is_fully_disposed = True

        return disposed, Money(basis_disposed)


@dataclass
class DeFiPosition:
    """A DeFi protocol position."""

    entity_id: UUID
    wallet_id: UUID
    protocol: DeFiProtocol
    position_type: DeFiPositionType
    network: BlockchainNetwork
    id: UUID = field(default_factory=uuid4)
    protocol_name: str | None = None  # For OTHER protocol type

    # Position details
    deposited_token_id: UUID | None = None
    deposited_amount: Decimal = Decimal("0")
    deposited_value_usd: Money = field(default_factory=lambda: Money(Decimal("0")))

    # For liquidity pools
    token_a_id: UUID | None = None
    token_b_id: UUID | None = None
    token_a_amount: Decimal | None = None
    token_b_amount: Decimal | None = None
    lp_token_amount: Decimal | None = None
    pool_share_percent: Decimal | None = None

    # Rewards/yield
    reward_token_id: UUID | None = None
    unclaimed_rewards: Decimal = Decimal("0")
    total_rewards_claimed: Decimal = Decimal("0")
    apy_current: Decimal | None = None  # Current APY

    # For lending/borrowing
    collateral_token_id: UUID | None = None
    collateral_amount: Decimal | None = None
    borrowed_token_id: UUID | None = None
    borrowed_amount: Decimal | None = None
    health_factor: Decimal | None = None
    liquidation_price: Decimal | None = None

    # Tracking
    entry_date: date | None = None
    entry_transaction_hash: str | None = None
    current_value_usd: Money | None = None
    last_updated: datetime | None = None

    is_active: bool = True
    notes: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @property
    def pnl(self) -> Money | None:
        """Profit/loss on position."""
        if self.current_value_usd is None:
            return None
        return Money(self.current_value_usd.amount - self.deposited_value_usd.amount)

    @property
    def pnl_percent(self) -> Decimal | None:
        """Profit/loss as percentage."""
        if self.current_value_usd is None or self.deposited_value_usd.amount == 0:
            return None
        return self.pnl.amount / self.deposited_value_usd.amount if self.pnl else None

    @property
    def is_at_risk(self) -> bool:
        """Whether position is at liquidation risk (for borrowing)."""
        if self.health_factor is None:
            return False
        return self.health_factor < Decimal("1.5")


@dataclass
class NFTCollection:
    """An NFT collection."""

    name: str
    network: BlockchainNetwork
    contract_address: str
    id: UUID = field(default_factory=uuid4)
    symbol: str | None = None
    total_supply: int | None = None
    floor_price: Money | None = None
    floor_price_updated: datetime | None = None
    opensea_slug: str | None = None
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class NFTHolding:
    """An NFT holding."""

    wallet_id: UUID
    collection_id: UUID
    token_id_on_chain: str  # The NFT's token ID on the blockchain
    id: UUID = field(default_factory=uuid4)
    name: str | None = None
    image_url: str | None = None
    metadata_url: str | None = None

    # Cost basis
    acquisition_date: date | None = None
    acquisition_cost: Money = field(default_factory=lambda: Money(Decimal("0")))
    acquisition_type: TransactionType = TransactionType.BUY
    acquisition_transaction_hash: str | None = None

    # Current value
    estimated_value: Money | None = None
    last_sale_price: Money | None = None
    value_updated: datetime | None = None

    # Disposition
    is_sold: bool = False
    sale_date: date | None = None
    sale_price: Money | None = None
    sale_transaction_hash: str | None = None

    notes: str | None = None
    created_at: datetime = field(default_factory=_utc_now)

    @property
    def realized_gain(self) -> Money | None:
        """Realized gain if sold."""
        if not self.is_sold or self.sale_price is None:
            return None
        return Money(self.sale_price.amount - self.acquisition_cost.amount)


@dataclass
class CryptoTransaction:
    """A cryptocurrency transaction for tracking and tax purposes."""

    wallet_id: UUID
    transaction_type: TransactionType
    timestamp: datetime
    id: UUID = field(default_factory=uuid4)

    # Transaction details
    transaction_hash: str | None = None
    network: BlockchainNetwork | None = None
    block_number: int | None = None

    # Tokens involved
    token_id: UUID | None = None
    quantity: Decimal = Decimal("0")

    # For swaps/trades
    from_token_id: UUID | None = None
    from_quantity: Decimal | None = None
    to_token_id: UUID | None = None
    to_quantity: Decimal | None = None

    # Values at time of transaction
    price_usd: Money | None = None
    value_usd: Money | None = None
    fee_amount: Decimal = Decimal("0")
    fee_token_id: UUID | None = None
    fee_usd: Money | None = None

    # Counterparty
    counterparty_address: str | None = None
    counterparty_wallet_id: UUID | None = None  # If internal transfer

    # Tax tracking
    cost_basis_used: Money | None = None
    realized_gain: Money | None = None
    tax_lot_ids_used: list[UUID] = field(default_factory=list)
    is_taxable: bool = True
    tax_treatment: str | None = None  # "short_term", "long_term", "income"

    notes: str | None = None
    created_at: datetime = field(default_factory=_utc_now)

    @property
    def date(self) -> date:
        """Transaction date."""
        return self.timestamp.date()
