"""Модели таблиц. Порядок важен: метрики ссылаются на заявку."""

from models.admin_data import AdminData
from models.lead import Lead
from models.lead_metrics import LeadMetrics

SCHEMA_MODELS = (Lead, LeadMetrics, AdminData)
