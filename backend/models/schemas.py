"""All Pydantic v2 request/response schemas for C1B API."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict


# ------- Auth -------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    token: str
    refresh_token: str
    role: str
    user_id: str
    is_existing_customer: bool
    email: str
    full_name: Optional[str] = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "customer"


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPayload(BaseModel):
    user_id: str
    email: str
    role: str
    exp: int


# ------- Pipeline -------
class IngestResponse(BaseModel):
    file_id: str
    status: str
    rows_detected: int
    columns_detected: List[str]
    message: str


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    column_checks: Dict[str, bool]


class FeatureVectorResponse(BaseModel):
    customer_id: str
    features: Dict[str, float]
    n_features: int


class ScoreRequest(BaseModel):
    customer_id: str
    feature_vector: Optional[Dict[str, float]] = None


class ScoreResponse(BaseModel):
    customer_id: str
    risk_label: str
    risk_score: float
    confidence: str
    contributing_factors: Dict[str, float]
    recommended_action: str
    recommended_apr: float
    credit_line_change: float
    current_limit: float
    recommended_limit: float
    model_version: str
    assessed_at: str


class BatchRunResponse(BaseModel):
    batch_id: str
    customers_scored: int
    eligible_expand: int
    high_risk: int
    medium_risk: int
    low_risk: int
    completed_at: str


# ------- Customer / Dashboard -------
class CustomerSummary(BaseModel):
    customer_id: str
    full_name: str
    risk_label: str
    risk_score: float
    credit_limit: float
    utilization_rate: float
    recommended_action: str


class CustomerProfile(BaseModel):
    customer_id: str
    full_name: str
    age: int
    income: float
    employment_status: str
    geography_region: str
    credit_limit: float
    current_balance: float
    utilization_rate: float
    bureau_score: int
    onboarding_date: str


class TransactionRow(BaseModel):
    trans_date: str
    post_date: str
    transaction_type: str
    description: str
    amount_usd: float
    reference_number: str


class RiskHistoryEntry(BaseModel):
    assessed_at: str
    risk_label: str
    risk_score: float
    model_version: str


class CreditDecision(BaseModel):
    customer_id: str
    risk_label: str
    risk_score: float
    action: str
    current_limit: float
    recommended_limit: float
    current_apr: float
    recommended_apr: float
    contributing_factors: Dict[str, float]
    opportunity_score: float
    opportunity_rank: int


class FullReport(BaseModel):
    profile: CustomerProfile
    phase1_features: Dict[str, float]
    phase2_risk: Dict[str, Any]
    phase3_decision: CreditDecision
    phase4_batch_status: Dict[str, Any]


class DashboardSummary(BaseModel):
    total_customers: int
    high_risk: int
    medium_risk: int
    low_risk: int
    avg_risk_score: float
    eligible_expand: int
    last_batch_run: str
    model_version: str
    roc_auc: float


# ------- Agent -------
class AgentChatRequest(BaseModel):
    session_id: str
    message: str
    customer_id: Optional[str] = None


class AgentChatResponse(BaseModel):
    session_id: str
    response: str
    tool_trace: List[Dict[str, Any]] = []
    flagged_for_review: bool = False


# ------- Errors -------
class ErrorResponse(BaseModel):
    error: str
    code: int
