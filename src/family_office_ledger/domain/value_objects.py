from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    CNY = "CNY"
    HKD = "HKD"
    SGD = "SGD"
    NZD = "NZD"
    SEK = "SEK"
    NOK = "NOK"
    DKK = "DKK"
    MXN = "MXN"
    BRL = "BRL"
    INR = "INR"
    KRW = "KRW"
    ZAR = "ZAR"


class LotSelection(str, Enum):
    FIFO = "fifo"
    LIFO = "lifo"
    SPECIFIC_ID = "specific_id"
    AVERAGE_COST = "average_cost"
    MINIMIZE_GAIN = "minimize_gain"
    MAXIMIZE_GAIN = "maximize_gain"
    HIFO = "hifo"


class EntityType(str, Enum):
    LLC = "llc"
    TRUST = "trust"
    PARTNERSHIP = "partnership"
    INDIVIDUAL = "individual"
    HOLDING_CO = "holding_co"


class AccountType(str, Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


class AccountSubType(str, Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    BROKERAGE = "brokerage"
    IRA = "ira"
    ROTH_IRA = "roth_ira"
    K401 = "401k"
    K529 = "529"
    REAL_ESTATE = "real_estate"
    PRIVATE_EQUITY = "private_equity"
    VENTURE_CAPITAL = "venture_capital"
    CRYPTO = "crypto"
    CASH = "cash"
    LOAN = "loan"
    OTHER = "other"


class AssetClass(str, Enum):
    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    ALTERNATIVE = "alternative"
    REAL_ESTATE = "real_estate"
    CRYPTO = "crypto"
    CASH = "cash"
    PRIVATE_EQUITY = "private_equity"
    VENTURE_CAPITAL = "venture_capital"


class AcquisitionType(str, Enum):
    PURCHASE = "purchase"
    GIFT = "gift"
    INHERITANCE = "inheritance"
    TRANSFER = "transfer"
    EXERCISE = "exercise"
    REINVESTMENT = "reinvestment"
    SPINOFF = "spinoff"
    MERGER = "merger"


class CorporateActionType(str, Enum):
    SPLIT = "split"
    REVERSE_SPLIT = "reverse_split"
    SPINOFF = "spinoff"
    MERGER = "merger"
    NAME_CHANGE = "name_change"
    SYMBOL_CHANGE = "symbol_change"
    DIVIDEND = "dividend"
    CLASS_CONVERSION = "class_conversion"


class TransactionType(str, Enum):
    INTEREST = "interest"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    TRUST_TRANSFER = "trust_transfer"
    CONTRIBUTION_DISTRIBUTION = "contribution_distribution"
    CONTRIBUTION_TO_ENTITY = "contribution_to_entity"
    LOAN = "loan"
    LOAN_REPAYMENT = "loan_repayment"
    PURCHASE_QSBS = "purchase_qsbs"
    PURCHASE_NON_QSBS = "purchase_non_qsbs"
    PURCHASE_OZ_FUND = "purchase_oz_fund"
    SALE_QSBS = "sale_qsbs"
    SALE_NON_QSBS = "sale_non_qsbs"
    LIQUIDATION = "liquidation"
    BROKER_FEES = "broker_fees"
    RETURN_OF_FUNDS = "return_of_funds"
    PUBLIC_MARKET = "public_market"
    UNCLASSIFIED = "unclassified"


class ExpenseCategory(str, Enum):
    PAYROLL = "payroll"
    RENT = "rent"
    UTILITIES = "utilities"
    INSURANCE = "insurance"
    LEGAL = "legal"
    ACCOUNTING = "accounting"
    CONSULTING = "consulting"
    TRAVEL = "travel"
    MEALS = "meals"
    ENTERTAINMENT = "entertainment"
    SOFTWARE = "software"
    HARDWARE = "hardware"
    HOSTING = "hosting"
    BANK_FEES = "bank_fees"
    INTEREST_EXPENSE = "interest_expense"
    OFFICE_SUPPLIES = "office_supplies"
    MARKETING = "marketing"
    CHARITABLE = "charitable"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: Currency | str = "USD"

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))

        if isinstance(self.currency, str):
            try:
                currency_enum = Currency[self.currency]
                object.__setattr__(self, "currency", currency_enum)
            except KeyError:
                raise ValueError(f"Invalid currency: {self.currency}")
        elif isinstance(self.currency, Currency):
            pass
        else:
            raise ValueError(f"Invalid currency: {self.currency}")

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {self.currency} and {other.currency}")
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: Decimal | int | float) -> "Money":
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.amount, self.currency)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

    def __lt__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare {self.currency} and {other.currency}")
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        return self == other or self < other

    @property
    def is_zero(self) -> bool:
        return self.amount == Decimal("0")

    @property
    def is_positive(self) -> bool:
        return self.amount > Decimal("0")

    @property
    def is_negative(self) -> bool:
        return self.amount < Decimal("0")

    @classmethod
    def zero(cls, currency: Currency | str = "USD") -> "Money":
        return cls(Decimal("0"), currency)


@dataclass(frozen=True, slots=True)
class Quantity:
    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(str(self.value)))

    def __add__(self, other: "Quantity") -> "Quantity":
        return Quantity(self.value + other.value)

    def __sub__(self, other: "Quantity") -> "Quantity":
        return Quantity(self.value - other.value)

    def __mul__(self, factor: Decimal | int | float) -> "Quantity":
        return Quantity(self.value * Decimal(str(factor)))

    def __neg__(self) -> "Quantity":
        return Quantity(-self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Quantity):
            return NotImplemented
        return self.value == other.value

    def __lt__(self, other: "Quantity") -> bool:
        return self.value < other.value

    def __le__(self, other: "Quantity") -> bool:
        return self == other or self < other

    @property
    def is_zero(self) -> bool:
        return self.value == Decimal("0")

    @property
    def is_positive(self) -> bool:
        return self.value > Decimal("0")

    @property
    def is_negative(self) -> bool:
        return self.value < Decimal("0")

    @classmethod
    def zero(cls) -> "Quantity":
        return cls(Decimal("0"))


__all__ = [
    "Currency",
    "LotSelection",
    "EntityType",
    "AccountType",
    "AccountSubType",
    "AssetClass",
    "AcquisitionType",
    "CorporateActionType",
    "TransactionType",
    "ExpenseCategory",
    "Money",
    "Quantity",
]
