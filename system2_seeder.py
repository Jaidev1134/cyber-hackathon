<<<<<<< HEAD
=======
"""
system2_seeder.py  —  SYSTEM 2: Canary Seeder + File Setup  [UPGRADED v2]
==========================================================================
Cyber Security Hackathon  |  Problem #24  |  Ransomware Defence

Upgrades over v1
----------------
  • Recursive subdirectory tree  (Finance/, HR/, DevOps/, Legal/, …)
    → Forces System 1 to use os.walk() / recursive traversal
  • 100+ files spread across the tree
    → "Terminal Matrix" effect during live demo
    → Stress-tests System 3 watchdog at scale
  • Canaries distributed at every depth level
    → No single folder is "safe" — detection fires anywhere
  • Trap files duplicated or mirrored across subtrees where appropriate
  • Detailed per-folder README decoys to pad realism

Folder layout produced  (abbreviated)
--------------------------------------
Safe_Target_Folder/
├── 00_huge_tarpit.dat          [T3]  hits first alphabetically
├── 000_passwords.txt           [CANARY]
├── AAA_crypto_keys.txt         [CANARY]
├── backup_archive.zip          [T5]  zip bomb (root level)
├── database.lck                [T4]  locked
├── meeting_notes.txt           normal
├── readonly_system.cfg         [T1]
├── Report (Final) 😊.txt       [T2]
├── ...more root normals...
│
├── Finance/
│   ├── 2023/
│   │   ├── Q1_report.xlsx      normal
│   │   ├── Q2_report.xlsx      normal
│   │   ├── Q3_report.xlsx      normal
│   │   ├── Q4_report.xlsx      normal
│   │   └── audit_trail.csv     normal
│   ├── 2024/
│   │   ├── budget_draft.xlsx   normal
│   │   ├── capex_forecast.csv  normal
│   │   └── 000_passwords.txt   [CANARY deep]
│   ├── payroll_master.csv      normal
│   └── vendor_contracts.pdf    normal
│
├── HR/
│   ├── Employees/
│   │   ├── alice_smith.docx    normal
│   │   ├── ... (10 employees)
│   │   └── AAA_crypto_keys.txt [CANARY deep]
│   ├── Policies/
│   │   ├── remote_work.pdf     normal
│   │   └── code_of_conduct.pdf normal
│   └── onboarding_checklist.docx normal
│
├── DevOps/
│   ├── Configs/
│   │   ├── nginx.conf          normal
│   │   ├── docker-compose.yml  normal
│   │   └── 00_tarpit_mirror.dat [T3 mirror]
│   ├── Scripts/
│   │   ├── deploy.sh           normal
│   │   └── backup.sh           normal
│   └── Secrets/
│       ├── 000_passwords.txt   [CANARY deep]
│       └── AAA_crypto_keys.txt [CANARY deep]
│
├── Legal/
│   ├── Contracts/
│   │   ├── vendor_nda_2024.pdf normal
│   │   └── saas_agreement.pdf  normal
│   └── Compliance/
│       ├── gdpr_report.docx    normal
│       └── iso27001_audit.pdf  normal
│
└── Projects/
    ├── Alpha/
    │   ├── spec.docx           normal
    │   └── roadmap.xlsx        normal
    ├── Beta/
    │   ├── design_doc.pdf      normal
    │   └── meeting_notes.txt   normal
    └── Archive/
        ├── old_codebase.zip    normal (small)
        └── 000_passwords.txt   [CANARY deep]
"""

>>>>>>> 1dd286d2b1793e40ec278d8c90fc78c49ada235c
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
<<<<<<< HEAD
from config import TEST_DIR, CANARY_REGISTRY

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
=======
>>>>>>> 1dd286d2b1793e40ec278d8c90fc78c49ada235c

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
<<<<<<< HEAD
TARGET_DIR = TEST_DIR
=======
TARGET_DIR = os.path.join(BASE_DIR, "Safe_Target_Folder")
>>>>>>> 1dd286d2b1793e40ec278d8c90fc78c49ada235c

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

<<<<<<< HEAD
TARPIT_SIZE_BYTES = 5 * 1024 * 1024   # 5 MB main tarpit (reduced to avoid huge delays)
TARPIT_ALT_BYTES  = 1 * 1024 * 1024   # 1 MB mirror
=======
TARPIT_SIZE_BYTES = 50 * 1024 * 1024   # 50 MB main tarpit
TARPIT_ALT_BYTES  =  5 * 1024 * 1024   #  5 MB mirror (DevOps subfolder)
>>>>>>> 1dd286d2b1793e40ec278d8c90fc78c49ada235c

# ---------------------------------------------------------------------------
# SUBDIRECTORY TREE DEFINITION
# ---------------------------------------------------------------------------
<<<<<<< HEAD
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

=======
# Each tuple: (relative_path_from_TARGET, list_of_normal_filenames)
SUBDIR_NORMAL_FILES = [
    # ── Finance ─────────────────────────────────────────────────────────────
    ("Finance", [
        "payroll_master.csv",
        "vendor_contracts.pdf",
        "expense_policy.docx",
    ]),
    ("Finance/2023", [
        "Q1_report.xlsx",
        "Q2_report.xlsx",
        "Q3_report.xlsx",
        "Q4_report.xlsx",
        "audit_trail.csv",
        "tax_filing_2023.pdf",
    ]),
    ("Finance/2024", [
        "budget_draft.xlsx",
        "capex_forecast.csv",
        "Q1_actuals.xlsx",
        "Q2_actuals.xlsx",
        "invoice_register.csv",
    ]),
    ("Finance/2025", [
        "q1_projections.xlsx",
        "annual_budget_v3.xlsx",
        "cash_flow_model.csv",
    ]),

    # ── HR ───────────────────────────────────────────────────────────────────
    ("HR", [
        "onboarding_checklist.docx",
        "org_chart_2026.pdf",
        "headcount_plan.xlsx",
    ]),
    ("HR/Employees", [
        "alice_smith.docx",
        "bob_jones.docx",
        "carol_white.docx",
        "dave_brown.docx",
        "eve_davis.docx",
        "frank_wilson.docx",
        "grace_taylor.docx",
        "henry_moore.docx",
        "irene_jackson.docx",
        "james_martin.docx",
    ]),
    ("HR/Policies", [
        "remote_work_policy.pdf",
        "code_of_conduct.pdf",
        "leave_policy.docx",
        "disciplinary_procedure.pdf",
    ]),
    ("HR/Recruitment", [
        "job_descriptions_2026.docx",
        "interview_scorecard.xlsx",
        "offer_letter_template.docx",
    ]),

    # ── DevOps ───────────────────────────────────────────────────────────────
    ("DevOps", [
        "runbook_prod.md",
        "incident_response.md",
        "architecture_overview.pdf",
    ]),
    ("DevOps/Configs", [
        "nginx.conf",
        "docker-compose.yml",
        "prometheus.yml",
        "grafana_dashboard.json",
        "haproxy.cfg",
    ]),
    ("DevOps/Scripts", [
        "deploy.sh",
        "backup.sh",
        "health_check.py",
        "db_migrate.py",
        "cleanup_logs.sh",
    ]),
    ("DevOps/Secrets", []),   # canaries only — see deep canary seeding below

    # ── Legal ────────────────────────────────────────────────────────────────
    ("Legal", [
        "litigation_register.xlsx",
        "ip_portfolio.pdf",
    ]),
    ("Legal/Contracts", [
        "vendor_nda_2024.pdf",
        "saas_agreement_acme.pdf",
        "partnership_mou.docx",
        "software_license_msft.pdf",
    ]),
    ("Legal/Compliance", [
        "gdpr_report_2025.docx",
        "iso27001_audit.pdf",
        "soc2_type2_report.pdf",
        "data_retention_policy.docx",
    ]),

    # ── Projects ─────────────────────────────────────────────────────────────
    ("Projects", [
        "project_registry.xlsx",
        "resource_allocation.xlsx",
    ]),
    ("Projects/Alpha", [
        "spec_v2.docx",
        "roadmap_alpha.xlsx",
        "stakeholder_map.pdf",
        "alpha_meeting_notes.txt",
    ]),
    ("Projects/Beta", [
        "design_doc_beta.pdf",
        "beta_meeting_notes.txt",
        "api_spec.yaml",
        "test_plan_beta.docx",
    ]),
    ("Projects/Archive", [
        "old_codebase.zip",
        "legacy_docs.pdf",
        "migration_notes.txt",
    ]),

    # ── IT ───────────────────────────────────────────────────────────────────
    ("IT", [
        "asset_inventory.xlsx",
        "network_diagram.pdf",
        "patch_schedule_2026.xlsx",
    ]),
    ("IT/Endpoints", [
        "laptop_registry.csv",
        "mdm_enrollment_log.csv",
        "software_licenses.xlsx",
    ]),
    ("IT/Backups", [
        "backup_policy.docx",
        "restore_test_log_2025.csv",
        "retention_schedule.pdf",
    ]),
]

# Deep-canary locations: (relative_dir, canary_basename)
>>>>>>> 1dd286d2b1793e40ec278d8c90fc78c49ada235c
DEEP_CANARIES = [
    ("Finance/2024",    CANARY_BASENAME_PASSWORDS),
    ("HR/Employees",    CANARY_BASENAME_AWSKEYS),
    ("DevOps/Secrets",  CANARY_BASENAME_PASSWORDS),
    ("DevOps/Secrets",  CANARY_BASENAME_AWSKEYS),
    ("Projects/Archive",CANARY_BASENAME_PASSWORDS),
    ("IT/Backups",      CANARY_BASENAME_PASSWORDS),
]

<<<<<<< HEAD
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
=======
# Root-level normal files
ROOT_NORMAL_FILES = [
    "meeting_notes.txt",
    "project_specs.docx",
    "q3_financials.csv",
    "user_data.log",
    "company_handbook.pdf",
    "it_helpdesk_faq.docx",
    "emergency_contacts.txt",
    "software_inventory.xlsx",
]

# ---------------------------------------------------------------------------
# FAKE DATA GENERATORS — Canary files
# ---------------------------------------------------------------------------

_FIRST    = ["alice","bob","carol","dave","eve","frank","grace","henry",
             "irene","james","karen","liam","maya","neil","olivia","peter",
             "quinn","rachel","sam","tina"]
_DOMAIN   = ["corp.internal","company.com","acme.net","globaltech.io",
             "enterprise.org"]
_SERVICES = ["vpn","rdp","ssh","gitlab","jenkins","jira","confluence",
             "aws-console","github-enterprise","splunk","grafana",
             "hashicorp-vault","okta-admin","pagerduty","datadog",
             "snowflake","tableau","salesforce"]


def _fake_password():
    words   = ["Summer","Winter","Dragon","Falcon","Shadow","Rocket",
               "Cipher","Neon","Storm","Apex","Nexus","Titan","Blaze",
               "Vortex","Pulse","Zenith"]
    symbols = ["!","@","#","$","&","*"]
    return (random.choice(words)
            + str(random.randint(10,99))
            + random.choice(symbols)
            + ''.join(random.choices(string.digits, k=2)))


def generate_passwords_content():
    lines = [
        "# Internal Credential Store — CONFIDENTIAL",
        "# Exported: 2026-05-23  |  Owner: IT-OPS",
        "# FORMAT: service | username | password | last_changed",
        "#" + "-"*62, "",
    ]
    for _ in range(random.randint(18, 28)):
        svc  = random.choice(_SERVICES)
        user = random.choice(_FIRST) + str(random.randint(1,99))
        dom  = random.choice(_DOMAIN)
        pw   = _fake_password()
        yr   = random.randint(2024,2026)
        mo   = str(random.randint(1,12)).zfill(2)
        dy   = str(random.randint(1,28)).zfill(2)
        lines.append(f"{svc:<26} {user}@{dom:<34} {pw:<22} {yr}-{mo}-{dy}")
    lines += ["", "# --- Admin backdoor accounts (rotate ASAP) ---"]
    for _ in range(4):
        user = "admin_" + ''.join(random.choices(string.ascii_lowercase, k=4))
        lines.append(f"{'root-ssh':<26} {user:<44} {_fake_password()}")
    lines += ["", "# --- Service account tokens ---"]
    for svc in random.sample(_SERVICES, 4):
        token = "tok_" + ''.join(random.choices(string.hexdigits.lower(), k=32))
        lines.append(f"# {svc}  →  {token}")
    return "\n".join(lines) + "\n"


def _fake_aws_key():
    kid = "FKIA" + ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=16))
    sec = ''.join(
        random.choices(string.ascii_letters + string.digits + "+/", k=40))
    return kid, sec


def generate_crypto_keys_content():
    lines = [
        "# AWS Credential Backup — CONFIDENTIAL",
        "# Last rotation audit: 2026-03-15  |  Owner: devops@corp.internal",
        "# DO NOT COMMIT — should live in Vault, not in repo",
        "#" + "-"*62, "",
    ]
    profiles = [
        ("default",          "us-east-1",    "Production account — root-level keys"),
        ("staging",          "us-west-2",    "Staging / pre-prod environment"),
        ("dev-sandbox",      "eu-central-1", "Developer sandbox, broad IAM"),
        ("ci-cd-pipeline",   "us-east-1",    "Jenkins/GitHub Actions service account"),
        ("data-lake-access", "ap-south-1",   "S3 + Athena access for analytics team"),
        ("dr-failover",      "us-west-1",    "Disaster recovery account — break-glass"),
        ("security-audit",   "eu-west-1",    "Read-only security scanning account"),
    ]
    for profile, region, note in profiles:
        kid, sec = _fake_aws_key()
        lines += [
            f"[{profile}]  # {note}",
            f"aws_access_key_id     = {kid}",
            f"aws_secret_access_key = {sec}",
            f"region                = {region}", "",
        ]
    lines += [
        "# --- GCP Service Account (JSON key export) ---", "",
        '# {"type": "service_account", "project_id": "corp-prod-339812",',
        f'#  "private_key_id": "{"".join(random.choices(string.hexdigits.lower(), k=40))}",',
        '#  "client_email": "svc-deploy@corp-prod-339812.iam.gserviceaccount.com"}',
        "",
        "# --- Old keys from migration (not yet revoked) ---",
        "# Check with platform team before deleting", "",
    ]
    for label in ["legacy-prod", "temp-migration-jan", "old-ci-runner"]:
        kid, sec = _fake_aws_key()
        lines += [f"# {label}", f"# access_key = {kid}",
                  f"# secret_key = {sec}", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# UTILITY
# ---------------------------------------------------------------------------
>>>>>>> 1dd286d2b1793e40ec278d8c90fc78c49ada235c

def sha256_of_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

<<<<<<< HEAD
def _rand_text(size=50):
    return ''.join(random.choices(string.ascii_letters + " ", k=size))

def _write_normal_file(filepath):
    filename = os.path.basename(filepath)
    content = f"========================================\nFILE: {filename}\nSTATUS: SECURE\n========================================\n\nThis is a highly confidential corporate document.\nPath: {filepath}\n\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content + _rand_text(100))
=======

def _rand_text(size=500):
    return ''.join(random.choices(
        string.ascii_letters + string.digits + " \n.,;:-_", k=size))


def _section(title):
    print(f"\n[SYSTEM 2] {'─'*10} {title} {'─'*10}")


def _write_normal_file(filepath):
    """Write a plausible-looking decoy file based on its extension."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in (".csv",):
        header = "id,date,amount,category,notes\n"
        rows   = "\n".join(
            f"{i},{random.randint(2023,2026)}-{random.randint(1,12):02d}-{random.randint(1,28):02d},"
            f"{random.uniform(100,99999):.2f},{'OpEx' if i%2==0 else 'CapEx'},{''.join(random.choices(string.ascii_letters,k=12))}"
            for i in range(1, random.randint(20, 60))
        )
        content = header + rows + "\n"
    elif ext in (".sh",):
        content = (
            "#!/bin/bash\n# Auto-generated deployment script\nset -euo pipefail\n\n"
            f"DEPLOY_ENV=\"{'prod' if random.random() > 0.5 else 'staging'}\"\n"
            "echo \"[deploy] Starting deployment for $DEPLOY_ENV\"\n"
            + _rand_text(300)
        )
    elif ext in (".py",):
        content = (
            "#!/usr/bin/env python3\n\"\"\"Auto-generated maintenance script.\"\"\"\n\n"
            "import os, sys, logging\n\nlogging.basicConfig(level=logging.INFO)\nlog = logging.getLogger(__name__)\n\n"
            "def main():\n    log.info('Starting...')\n    " + _rand_text(200).replace("\n","\\n") + "\n\n"
            "if __name__ == '__main__':\n    main()\n"
        )
    elif ext in (".yml", ".yaml"):
        content = (
            f"version: '3.9'\nservices:\n  app:\n    image: corp/app:{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,20)}\n"
            "    ports:\n      - \"8080:8080\"\n    environment:\n"
            "      - NODE_ENV=production\n      - LOG_LEVEL=info\n"
        )
    elif ext in (".conf", ".cfg"):
        content = (
            "# System configuration — auto-generated\n"
            f"[global]\nworkers = {random.randint(2,16)}\ntimeout = {random.randint(30,120)}\n"
            f"log_level = {'INFO' if random.random() > 0.5 else 'WARNING'}\n"
        )
    elif ext in (".json",):
        content = json.dumps({
            "version": f"{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,30)}",
            "environment": random.choice(["production","staging","dev"]),
            "features": {f"feature_{i}": random.choice([True,False]) for i in range(5)},
            "metadata": {"generated": "2026-05-23", "owner": random.choice(_FIRST)},
        }, indent=2)
    elif ext in (".md",):
        content = (
            f"# {os.path.splitext(os.path.basename(filepath))[0].replace('_',' ').title()}\n\n"
            "> Auto-generated internal document.\n\n"
            "## Overview\n\n" + _rand_text(300) + "\n\n"
            "## Details\n\n" + _rand_text(300) + "\n"
        )
    else:
        # .txt, .docx, .pdf, .xlsx etc. — just write plausible text
        content = "CONFIDENTIAL — INTERNAL USE ONLY\n\n" + _rand_text(random.randint(400, 900))
    with open(filepath, "w", encoding="utf-8", errors="replace") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# TRAP FILE CREATORS  (unchanged from v1 except tarpit accepts size param)
# ---------------------------------------------------------------------------

def seed_trap_readonly(directory):
    """T1 — Read-Only File → chmod 444"""
    filepath = os.path.join(directory, TRAP_READONLY)
    if os.path.exists(filepath):
        try:
            os.chmod(filepath, stat.S_IRUSR | stat.S_IWUSR |
                               stat.S_IRGRP | stat.S_IWGRP |
                               stat.S_IROTH | stat.S_IWOTH)
        except Exception:
            pass
    content = (
        "# /etc/system.cfg — Core Runtime Configuration\n"
        "# OWNER: SYSTEM  |  DO NOT MODIFY MANUALLY\n"
        "# Last validated: 2026-05-01T08:00:00Z\n"
        "#" + "-"*60 + "\n\n"
        "[runtime]\n"
        f"max_connections = {random.randint(512,4096)}\n"
        f"thread_pool     = {random.randint(16,128)}\n"
        "log_level       = WARNING\n"
        "secret_key      = "
        + ''.join(random.choices(string.hexdigits, k=48)) + "\n\n"
        "[database]\n"
        "host            = db-prod-01.corp.internal\n"
        "port            = 5432\n"
        "name            = prod_core\n"
        "user            = svc_runtime\n"
        "password        = " + _fake_password() + "\n"
    )
    with open(filepath, "w") as f:
        f.write(content)
    os.chmod(filepath, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    print(f"  [T1] Read-Only     : {TRAP_READONLY}  →  chmod 444")
    return filepath


def seed_trap_weird_name(directory):
    """T2 — Unicode + spaces + emoji in filename"""
    filepath = os.path.join(directory, TRAP_WEIRD_NAME)
    content = (
        "Q3 Strategy Review — FINAL APPROVED VERSION\n"
        "Prepared by: Strategy & Operations Team\n"
        "Date: 2026-04-30\n\n"
        + _rand_text(600)
    )
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [T2] Weird Name    : {TRAP_WEIRD_NAME}")
    return filepath


def seed_trap_tarpit(directory, filename=None, size_bytes=None):
    """T3 — Tar-Pit File: high-entropy, alphabetically first"""
    filename   = filename   or TRAP_TARPIT
    size_bytes = size_bytes or TARPIT_SIZE_BYTES
    filepath   = os.path.join(directory, filename)
    chunk = 1024 * 1024
    written = 0
    with open(filepath, "wb") as f:
        while written < size_bytes:
            to_write = min(chunk, size_bytes - written)
            f.write(os.urandom(to_write))
            written += to_write
    size_mb = size_bytes / (1024 * 1024)
    print(f"  [T3] Tar-Pit       : {filename}  ({size_mb:.0f} MB random bytes)")
    return filepath


_lock_handle = None
_lock_thread = None
_lock_stop   = threading.Event()


def _hold_file_open(filepath, stop_event):
    try:
        fh = open(filepath, "r+b")
        if platform.system() != "Windows":
            try:
                import fcntl
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (ImportError, OSError):
                pass
        while not stop_event.is_set():
            time.sleep(0.5)
        fh.close()
    except Exception as e:
        print(f"  [T4] Lock thread warning: {e}")


def seed_trap_locked(directory):
    """T4 — Locked / In-Use File (background thread holds exclusive lock)"""
    global _lock_handle, _lock_thread, _lock_stop
    filepath = os.path.join(directory, TRAP_LOCKED)
    sqlite_magic = b"SQLite format 3\x00"
    with open(filepath, "wb") as f:
        f.write(sqlite_magic)
        f.write(os.urandom(96))
        f.write(b"\n-- Active session log --\n")
        f.write((_rand_text(300)).encode("utf-8"))
    _lock_stop.clear()
    _lock_thread = threading.Thread(
        target=_hold_file_open,
        args=(filepath, _lock_stop),
        daemon=True,
        name="T4-LockHolder",
    )
    _lock_thread.start()
    time.sleep(0.15)
    lock_type = "fcntl LOCK_EX" if platform.system() != "Windows" else "mandatory OS lock"
    print(f"  [T4] Locked File   : {TRAP_LOCKED}  ({lock_type})")
    return filepath


def seed_trap_zipbomb(directory):
    """T5 — Zip Bomb: ~10 KB on disk → 500 MB decompressed"""
    filepath = os.path.join(directory, TRAP_ZIPBOMB)
    BOMB_UNCOMPRESSED = 500 * 1024 * 1024
    CHUNK = 1024 * 1024
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as zf:
        info = zipfile.ZipInfo("backup_full_export.sql")
        info.compress_type = zipfile.ZIP_DEFLATED
        with zf.open(info, "w", force_zip64=True) as zentry:
            remaining = BOMB_UNCOMPRESSED
            null_chunk = b"\x00" * CHUNK
            while remaining > 0:
                to_write = min(CHUNK, remaining)
                zentry.write(null_chunk[:to_write])
                remaining -= to_write
    with open(filepath, "wb") as f:
        f.write(buf.getvalue())
    on_disk_kb = os.path.getsize(filepath) / 1024
    bomb_mb    = BOMB_UNCOMPRESSED / (1024 * 1024)
    ratio      = BOMB_UNCOMPRESSED / max(os.path.getsize(filepath), 1)
    print(f"  [T5] Zip Bomb      : {TRAP_ZIPBOMB}  "
          f"({on_disk_kb:.1f} KB → {bomb_mb:.0f} MB, ratio {ratio:.0f}:1)")
    return filepath

>>>>>>> 1dd286d2b1793e40ec278d8c90fc78c49ada235c

# ---------------------------------------------------------------------------
# MAIN SETUP
# ---------------------------------------------------------------------------
<<<<<<< HEAD
def setup_environment():
    print("[SYSTEM 2] ═══════════════════════════════════════════════")
    print("[SYSTEM 2]  Ransomware Defence Lab — Environment Seeder   ")
    print("[SYSTEM 2] ═══════════════════════════════════════════════")
    os.makedirs(TARGET_DIR, exist_ok=True)

    canary_registry = {}

=======

def setup_environment():
    print("[SYSTEM 2] ═══════════════════════════════════════════════")
    print("[SYSTEM 2]  Ransomware Defence Lab — Environment Seeder   ")
    print("[SYSTEM 2]  VERSION 2  —  100+ files, recursive subtree   ")
    print("[SYSTEM 2] ═══════════════════════════════════════════════")
    print(f"[SYSTEM 2] Base dir  : {BASE_DIR}")
    print(f"[SYSTEM 2] Target dir: {TARGET_DIR}")

    os.makedirs(TARGET_DIR, exist_ok=True)

    file_count       = 0
    canary_registry  = {}   # filename_key → {path, sha256}

    # ── Helper: write + register a canary ──────────────────────────────────
>>>>>>> 1dd286d2b1793e40ec278d8c90fc78c49ada235c
    def _seed_canary(directory, basename, generator_fn):
        fp = os.path.join(directory, basename)
        with open(fp, "w", encoding="utf-8") as fh:
            fh.write(generator_fn())
        fhash = sha256_of_file(fp)
<<<<<<< HEAD
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
=======
        rel   = os.path.relpath(fp, BASE_DIR)
        canary_registry[rel] = {"path": fp, "sha256": fhash}
        print(f"    [CANARY] {rel}")
        print(f"             SHA-256 : {fhash}")
        return fp

    # ══════════════════════════════════════════════════════════════════════
    # 1. ROOT-LEVEL normal files
    # ══════════════════════════════════════════════════════════════════════
    _section("Root-level Normal Files")
    for filename in ROOT_NORMAL_FILES:
        fp = os.path.join(TARGET_DIR, filename)
        _write_normal_file(fp)
        print(f"  [OK]  {filename}")
        file_count += 1
    print(f"\n  {len(ROOT_NORMAL_FILES)} root normal files seeded.")

    # ══════════════════════════════════════════════════════════════════════
    # 2. ROOT-LEVEL canary files
    # ══════════════════════════════════════════════════════════════════════
    _section("Root-level Canary Files")
    _seed_canary(TARGET_DIR, CANARY_BASENAME_PASSWORDS, generate_passwords_content)
    _seed_canary(TARGET_DIR, CANARY_BASENAME_AWSKEYS,   generate_crypto_keys_content)
    file_count += 2

    # ══════════════════════════════════════════════════════════════════════
    # 3. ROOT-LEVEL trap files
    # ══════════════════════════════════════════════════════════════════════
    _section("Root-level Trap Files")
    trap_files = {}

    fp = seed_trap_tarpit(TARGET_DIR)
    trap_files[TRAP_TARPIT]     = {"path": fp, "trap_type": "tar-pit",
                                   "effect": "MemoryError / slowdown on read-all"}
    fp = seed_trap_readonly(TARGET_DIR)
    trap_files[TRAP_READONLY]   = {"path": fp, "trap_type": "read-only",
                                   "effect": "PermissionError on write"}
    fp = seed_trap_weird_name(TARGET_DIR)
    trap_files[TRAP_WEIRD_NAME] = {"path": fp, "trap_type": "weird-name",
                                   "effect": "UnicodeDecodeError / path crash"}
    fp = seed_trap_locked(TARGET_DIR)
    trap_files[TRAP_LOCKED]     = {"path": fp, "trap_type": "locked",
                                   "effect": "PermissionError (file in use)"}
    fp = seed_trap_zipbomb(TARGET_DIR)
    trap_files[TRAP_ZIPBOMB]    = {"path": fp, "trap_type": "zip-bomb",
                                   "effect": "MemoryError / disk exhaustion on extract"}
    file_count += 5

    # ══════════════════════════════════════════════════════════════════════
    # 4. SUBDIRECTORY TREE — normal files
    # ══════════════════════════════════════════════════════════════════════
    _section("Subdirectory Tree — Normal Files")
    subdir_file_count = 0
>>>>>>> 1dd286d2b1793e40ec278d8c90fc78c49ada235c
    for rel_dir, filenames in SUBDIR_NORMAL_FILES:
        abs_dir = os.path.join(TARGET_DIR, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)
        for filename in filenames:
<<<<<<< HEAD
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
=======
            fp = os.path.join(abs_dir, filename)
            _write_normal_file(fp)
            subdir_file_count += 1
            file_count        += 1
        if filenames:
            print(f"  [OK]  {rel_dir}/  →  {len(filenames)} files")
    print(f"\n  {subdir_file_count} subdirectory normal files seeded.")

    # ══════════════════════════════════════════════════════════════════════
    # 5. DEEP CANARY files — scattered through subdirs
    # ══════════════════════════════════════════════════════════════════════
    _section("Deep Canary Files (distributed across subtree)")
    for rel_dir, basename in DEEP_CANARIES:
        abs_dir = os.path.join(TARGET_DIR, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)
        gen_fn  = (generate_passwords_content if basename == CANARY_BASENAME_PASSWORDS
                   else generate_crypto_keys_content)
        _seed_canary(abs_dir, basename, gen_fn)
        file_count += 1

    # ══════════════════════════════════════════════════════════════════════
    # 6. SECONDARY TARPIT in DevOps/Configs  (hits early inside that subtree)
    # ══════════════════════════════════════════════════════════════════════
    _section("Secondary Trap Files in Subtrees")
    devops_configs = os.path.join(TARGET_DIR, "DevOps", "Configs")
    os.makedirs(devops_configs, exist_ok=True)
    fp = seed_trap_tarpit(devops_configs,
                          filename=TRAP_TARPIT_ALT,
                          size_bytes=TARPIT_ALT_BYTES)
    trap_files[f"DevOps/Configs/{TRAP_TARPIT_ALT}"] = {
        "path":      fp,
        "trap_type": "tar-pit-secondary",
        "effect":    "MemoryError / slowdown — hits first inside DevOps/Configs",
    }
    file_count += 1

    # ══════════════════════════════════════════════════════════════════════
    # 7. EXPORT canary_config.json for System 3
    # ══════════════════════════════════════════════════════════════════════
    _section("Exporting canary_config.json")

    # Count actual files via os.walk for accuracy
    actual_count = sum(len(files) for _, _, files in os.walk(TARGET_DIR))

    config = {
        "target_directory":   TARGET_DIR,
        "canary_files":       canary_registry,
        "trap_files":         trap_files,
        "total_files_seeded": actual_count,
        "platform":           platform.system(),
        "seeded_at":          time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version":            "2.0",
    }
    config_path = os.path.join(BASE_DIR, "canary_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print(f"  Config written → {config_path}")

    # ══════════════════════════════════════════════════════════════════════
    # 8. SUMMARY
    # ══════════════════════════════════════════════════════════════════════
    _section("Summary")
    print(f"  Subdirectories   : {sum(1 for _ in os.walk(TARGET_DIR)) - 1}")
    print(f"  Root normal      : {len(ROOT_NORMAL_FILES)}")
    print(f"  Subdir normal    : {subdir_file_count}")
    print(f"  Canary files     : {len(canary_registry)}  (root + deep, all hashed)")
    print(f"  Trap files       : {len(trap_files)}")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Total on disk    : {actual_count} files across {TARGET_DIR}")
    print()
    print("[SYSTEM 2] ✓ Environment ready.")
    print("[SYSTEM 2]   System 1 (ransomware sim) can target Safe_Target_Folder/")
    print("[SYSTEM 2]   System 1 must use os.walk() to traverse all subdirs")
    print("[SYSTEM 2]   System 3 (watchdog) loads canary_config.json")
    print()
    print("[SYSTEM 2]   NOTE: T4 lock thread still running.")
    print("[SYSTEM 2]   Keep this terminal open during the demo.")
    print("[SYSTEM 2]   Press Ctrl+C to release lock and exit cleanly.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SYSTEM 2] Shutdown signal received.")
        _lock_stop.set()
        if _lock_thread:
            _lock_thread.join(timeout=2)
        print("[SYSTEM 2] Lock released. Goodbye.")


if __name__ == "__main__":
    setup_environment()
>>>>>>> 1dd286d2b1793e40ec278d8c90fc78c49ada235c
