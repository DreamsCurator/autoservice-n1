"""Модели таблиц. Порядок важен: метрики ссылаются на заявку."""

from models.admin_data import AdminData
from models.admin_user import AdminUser
from models.lead import Lead
from models.lead_metrics import LeadMetrics, VisitMetric

SCHEMA_MODELS = (Lead, LeadMetrics, VisitMetric, AdminData, AdminUser)
