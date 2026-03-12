#!/bin/bash
# ============================================================
# Vayuntra — Live Demo Script
# Injects threats one by one to show real-time detection
# Run: bash demo.sh
# ============================================================

BASE="http://localhost:8000"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║       VAYUNTRA — Live Threat Injection Demo          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Get token ────────────────────────────────────────
echo "🔐 Authenticating..."
TOKEN=$(curl -s -X POST $BASE/api/v1/auth/login \
  -d "username=admin@vayuntra.demo&password=Vayuntra@123" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed — is the server running? (python start.py)"
  exit 1
fi

echo "✅ Token obtained"
echo ""
echo "🚨 Starting threat injection — watch http://localhost:8000"
echo ""

# ── Helper function ──────────────────────────────────────────
inject() {
  local json="$1"
  local label="$2"
  local delay="$3"
  
  curl -s -X POST $BASE/api/v1/threats/ \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$json" > /dev/null
  
  echo "🔴 INJECTED: $label"
  echo "   → Refresh dashboard now"
  echo ""
  sleep $delay
}

# ── Step 2: Inject threats one by one ───────────────────────

inject '{"title":"Ransomware Pre-Detonation — WORKSTATION-047","severity":"critical","mitre_tactic":"Impact","mitre_technique":"T1486","source_ip":"172.16.0.47","dest_ip":"185.220.101.34","process_name":"unknown.exe","confidence_score":0.97,"anomaly_score":0.94,"description":"Mass file encryption on WORKSTATION-047. 2000+ files renamed .locked. Shadow copies deleted."}' \
  "Ransomware Pre-Detonation [CRITICAL]" 5

inject '{"title":"C2 Beacon — Cobalt Strike Active","severity":"critical","mitre_tactic":"Command and Control","mitre_technique":"T1071","source_ip":"172.16.0.23","dest_ip":"45.33.32.156","process_name":"svchost.exe","confidence_score":0.93,"anomaly_score":0.91,"description":"Cobalt Strike beacon communicating with C2 every 60s. Encrypted over port 443."}' \
  "C2 Beacon — Cobalt Strike [CRITICAL]" 5

inject '{"title":"LSASS Dump — Mimikatz Credential Theft","severity":"critical","mitre_tactic":"Credential Access","mitre_technique":"T1003","source_ip":"172.16.0.8","process_name":"mimikatz.exe","confidence_score":0.99,"anomaly_score":0.97,"description":"Mimikatz dumping LSASS. All domain credentials compromised. Reset passwords immediately."}' \
  "LSASS Dump — Mimikatz [CRITICAL]" 5

inject '{"title":"Lateral Movement — Pass-the-Hash via SMB","severity":"high","mitre_tactic":"Lateral Movement","mitre_technique":"T1550","source_ip":"172.16.0.12","dest_ip":"172.16.0.1","process_name":"lsass.exe","confidence_score":0.85,"anomaly_score":0.82,"description":"NTLM hash reused to authenticate to domain controller without plaintext password."}' \
  "Lateral Movement — Pass-the-Hash [HIGH]" 5

inject '{"title":"DNS Tunneling — Covert Exfiltration Channel","severity":"high","mitre_tactic":"Exfiltration","mitre_technique":"T1048","source_ip":"172.16.0.44","dest_ip":"8.8.8.8","process_name":"dns.exe","confidence_score":0.83,"anomaly_score":0.79,"description":"Data encoded in DNS queries. 3200 queries/min to single resolver. Exfiltrating 50KB/min."}' \
  "DNS Tunneling [HIGH]" 5

inject '{"title":"Zero-Day Exploit — Log4Shell RCE","severity":"critical","mitre_tactic":"Initial Access","mitre_technique":"T1190","source_ip":"45.155.205.233","dest_ip":"172.16.0.1","process_name":"java.exe","confidence_score":0.99,"anomaly_score":0.98,"description":"Log4Shell CVE-2021-44228 exploitation. JNDI lookup in HTTP header triggering remote class load."}' \
  "Zero-Day Log4Shell [CRITICAL]" 5

inject '{"title":"Privilege Escalation — Token Impersonation","severity":"high","mitre_tactic":"Privilege Escalation","mitre_technique":"T1134","source_ip":"172.16.0.31","process_name":"cmd.exe","confidence_score":0.86,"anomaly_score":0.83,"description":"PrintSpoofer technique. Low-privilege process duplicating SYSTEM token via SeImpersonatePrivilege."}' \
  "Privilege Escalation [HIGH]" 5

inject '{"title":"Cryptominer — XMRig CPU 98%","severity":"medium","mitre_tactic":"Impact","mitre_technique":"T1496","source_ip":"172.16.0.38","dest_ip":"pool.minexmr.com","process_name":"xmrig.exe","confidence_score":0.95,"anomaly_score":0.93,"description":"XMRig mining Monero on production server. CPU at 98% for 6 hours. Mining pool: minexmr.com:3333."}' \
  "Cryptominer XMRig [MEDIUM]" 5

inject '{"title":"Brute Force — SSH 8400 Failed Attempts","severity":"medium","mitre_tactic":"Credential Access","mitre_technique":"T1110","source_ip":"185.180.143.49","dest_ip":"172.16.0.10","process_name":"sshd","confidence_score":0.78,"anomaly_score":0.75,"description":"8400 failed SSH login attempts in 30 minutes from Romanian IP. Targeting root and admin accounts."}' \
  "SSH Brute Force [MEDIUM]" 5

inject '{"title":"Supply Chain — Malicious NPM Package","severity":"critical","mitre_tactic":"Initial Access","mitre_technique":"T1195","source_ip":"172.16.0.55","dest_ip":"npmjs.com","process_name":"node.exe","confidence_score":0.94,"anomaly_score":0.92,"description":"Trojanized NPM package exfiltrating AWS_SECRET_ACCESS_KEY via postinstall hook."}' \
  "Supply Chain NPM Attack [CRITICAL]" 3

echo "══════════════════════════════════════════════════════"
echo "✅ 10 threats injected successfully"
echo ""
echo "   Now on dashboard:"
echo "   1. Click VIEW on any threat"
echo "   2. Click ISOLATE — endpoint gets contained"
echo "   3. Click REMEDIATE — AI generates playbook"
echo ""
echo "   API Docs: http://localhost:8000/api/docs"
echo "══════════════════════════════════════════════════════"
