import hashlib
import io
import json
import os
import platform
import random
import stat
import string
import sys
import threading
import time
import zipfile
from config import TEST_DIR, CANARY_REGISTRY

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = TEST_DIR

# Root-level canary basenames (also seeded deep inside subdirs)
CANARY_BASENAME_PASSWORDS   = "000_passwords.txt"
CANARY_BASENAME_AWSKEYS     = "AAA_crypto_keys.txt"

# Trap names
TRAP_READONLY   = "readonly_system.cfg"
TRAP_WEIRD_NAME = "Report (Final) \U0001f60a.txt"
TRAP_TARPIT     = "00_huge_tarpit.dat"
TRAP_TARPIT_ALT = "00_tarpit_mirror.dat"   # secondary tarpit in DevOps/Configs
TRAP_LOCKED     = "database.lck"
TRAP_ZIPBOMB    = "backup_archive.zip"

TARPIT_SIZE_BYTES = 5 * 1024 * 1024   # 5 MB main tarpit (reduced to avoid huge delays)
TARPIT_ALT_BYTES  = 1 * 1024 * 1024   # 1 MB mirror

# ---------------------------------------------------------------------------
# SUBDIRECTORY TREE DEFINITION
# ---------------------------------------------------------------------------
SUBDIR_NORMAL_FILES = [
    ("Finance", ["payroll_master.csv", "vendor_contracts.pdf", "expense_policy.docx"]),
    ("Finance/2023", ["Q1_report.xlsx", "Q2_report.xlsx", "Q3_report.xlsx", "Q4_report.xlsx", "audit_trail.csv", "tax_filing_2023.pdf"]),
    ("Finance/2024", ["budget_draft.xlsx", "capex_forecast.csv", "Q1_actuals.xlsx", "Q2_actuals.xlsx", "invoice_register.csv"]),
    ("Finance/2025", ["q1_projections.xlsx", "annual_budget_v3.xlsx", "cash_flow_model.csv"]),
    ("HR", ["onboarding_checklist.docx", "org_chart_2026.pdf", "headcount_plan.xlsx"]),
    ("HR/Employees", ["alice_smith.docx", "bob_jones.docx", "carol_white.docx", "dave_brown.docx", "eve_davis.docx", "frank_wilson.docx", "grace_taylor.docx", "henry_moore.docx", "irene_jackson.docx", "james_martin.docx"]),
    ("HR/Policies", ["remote_work_policy.pdf", "code_of_conduct.pdf", "leave_policy.docx", "disciplinary_procedure.pdf"]),
    ("HR/Recruitment", ["job_descriptions_2026.docx", "interview_scorecard.xlsx", "offer_letter_template.docx"]),
    ("DevOps", ["runbook_prod.md", "incident_response.md", "architecture_overview.pdf"]),
    ("DevOps/Configs", ["nginx.conf", "docker-compose.yml", "prometheus.yml", "grafana_dashboard.json", "haproxy.cfg"]),
    ("DevOps/Scripts", ["deploy.sh", "backup.sh", "health_check.py", "db_migrate.py", "cleanup_logs.sh"]),
    ("DevOps/Secrets", []),
    ("Legal", ["litigation_register.xlsx", "ip_portfolio.pdf"]),
    ("Legal/Contracts", ["vendor_nda_2024.pdf", "saas_agreement_acme.pdf", "partnership_mou.docx", "software_license_msft.pdf"]),
    ("Legal/Compliance", ["gdpr_report_2025.docx", "iso27001_audit.pdf", "soc2_type2_report.pdf", "data_retention_policy.docx"]),
    ("Projects", ["project_registry.xlsx", "resource_allocation.xlsx"]),
    ("Projects/Alpha", ["spec_v2.docx", "roadmap_alpha.xlsx", "stakeholder_map.pdf", "alpha_meeting_notes.txt"]),
    ("Projects/Beta", ["design_doc_beta.pdf", "beta_meeting_notes.txt", "api_spec.yaml", "test_plan_beta.docx"]),
    ("Projects/Archive", ["old_codebase.zip", "legacy_docs.pdf", "migration_notes.txt"]),
    ("IT", ["asset_inventory.xlsx", "network_diagram.pdf", "patch_schedule_2026.xlsx"]),
    ("IT/Endpoints", ["laptop_registry.csv", "mdm_enrollment_log.csv", "software_licenses.xlsx"]),
    ("IT/Backups", ["backup_policy.docx", "restore_test_log_2025.csv", "retention_schedule.pdf"]),
]

DEEP_CANARIES = [
    ("Finance/2024",    CANARY_BASENAME_PASSWORDS),
    ("HR/Employees",    CANARY_BASENAME_AWSKEYS),
    ("DevOps/Secrets",  CANARY_BASENAME_PASSWORDS),
    ("DevOps/Secrets",  CANARY_BASENAME_AWSKEYS),
    ("Projects/Archive",CANARY_BASENAME_PASSWORDS),
    ("IT/Backups",      CANARY_BASENAME_PASSWORDS),
]

ROOT_NORMAL_FILES = [
    "meeting_notes.txt", "project_specs.docx", "q3_financials.csv", "user_data.log",
    "company_handbook.pdf", "it_helpdesk_faq.docx", "emergency_contacts.txt", "software_inventory.xlsx",
]

# ---------------------------------------------------------------------------
# FAKE DATA GENERATORS
# ---------------------------------------------------------------------------
_FIRST    = ["alice","bob","carol","dave","eve","frank","grace","henry","irene","james"]
_DOMAIN   = ["corp.internal","company.com","acme.net"]
_SERVICES = ["vpn","rdp","ssh","gitlab","aws-console"]

def _fake_password():
    words = ["Summer","Winter","Dragon","Falcon"]
    return random.choice(words) + str(random.randint(10,99)) + "!"

def generate_passwords_content():
    lines = ["# Internal Credential Store — CONFIDENTIAL", "#" + "-"*62, ""]
    for _ in range(5):
        lines.append(f"{random.choice(_SERVICES):<26} {random.choice(_FIRST)}@{random.choice(_DOMAIN):<34} {_fake_password()}")
    return "\n".join(lines) + "\n"

def generate_crypto_keys_content():
    return "# AWS Credential Backup — CONFIDENTIAL\naws_access_key_id = AKIAIOSFODNN7EXAMPLE\naws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n"

def sha256_of_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def _rand_text(size=50):
    return ''.join(random.choices(string.ascii_letters + " ", k=size))

def _write_normal_file(filepath):
    filename = os.path.basename(filepath)
    content = f"========================================\nFILE: {filename}\nSTATUS: SECURE\n========================================\n\nThis is a highly confidential corporate document.\nPath: {filepath}\n\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content + _rand_text(100))

# ---------------------------------------------------------------------------
# MAIN SETUP
# ---------------------------------------------------------------------------
def setup_environment():
    print("[SYSTEM 2] ═══════════════════════════════════════════════")
    print("[SYSTEM 2]  Ransomware Defence Lab — Environment Seeder   ")
    print("[SYSTEM 2] ═══════════════════════════════════════════════")
    os.makedirs(TARGET_DIR, exist_ok=True)

    canary_registry = {}

    def _seed_canary(directory, basename, generator_fn):
        fp = os.path.join(directory, basename)
        with open(fp, "w", encoding="utf-8") as fh:
            fh.write(generator_fn())
        fhash = sha256_of_file(fp)
        rel = os.path.relpath(fp, BASE_DIR)
        canary_registry[rel] = {"path": fp, "sha256": fhash}
        print(f"    [CANARY] {rel}")
        return fp

    # 1. Root files
    for filename in ROOT_NORMAL_FILES:
        _write_normal_file(os.path.join(TARGET_DIR, filename))
    
    _seed_canary(TARGET_DIR, CANARY_BASENAME_PASSWORDS, generate_passwords_content)
    _seed_canary(TARGET_DIR, CANARY_BASENAME_AWSKEYS, generate_crypto_keys_content)
    
    # Absolute first canary
    _seed_canary(TARGET_DIR, "!00_canary_alpha.txt", generate_passwords_content)

    # 2. Subdirectories
    for rel_dir, filenames in SUBDIR_NORMAL_FILES:
        abs_dir = os.path.join(TARGET_DIR, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)
        for filename in filenames:
            _write_normal_file(os.path.join(abs_dir, filename))

    # 3. Deep canaries
    for rel_dir, basename in DEEP_CANARIES:
        abs_dir = os.path.join(TARGET_DIR, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)
        _seed_canary(abs_dir, basename, generate_passwords_content)

    # Write registry for watchdog
    config = {
        "target_directory": TARGET_DIR,
        "canary_files": canary_registry,
    }
    
    # We must write to the canonical registry file location expected by main/canary_monitor
    os.makedirs(os.path.dirname(CANARY_REGISTRY), exist_ok=True)
    with open(CANARY_REGISTRY, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    print(f"[SYSTEM 2] Config written → {CANARY_REGISTRY}")
    print("[SYSTEM 2] ✓ Environment ready.")

if __name__ == "__main__":
    setup_environment()
