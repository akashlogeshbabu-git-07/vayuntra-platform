export type ThreatSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type ThreatStatus = 'detected' | 'investigating' | 'contained' | 'remediated' | 'false_positive' | 'closed';
export type AgentStatus = 'online' | 'offline' | 'isolated' | 'updating' | 'error';
export type AgentOS = 'windows' | 'linux' | 'macos';

export interface Threat {
  id: string;
  tenant_id: string;
  agent_id?: string;
  title: string;
  description?: string;
  severity: ThreatSeverity;
  status: ThreatStatus;
  confidence_score: number;
  anomaly_score: number;
  mitre_tactic?: string;
  mitre_technique?: string;
  source_ip?: string;
  dest_ip?: string;
  process_name?: string;
  evidence?: Record<string, any>;
  remediation_playbook?: string;
  analyst_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface Agent {
  id: string;
  tenant_id: string;
  hostname: string;
  ip_address: string;
  os: AgentOS;
  os_version?: string;
  agent_version: string;
  status: AgentStatus;
  last_seen?: string;
  tags?: Record<string, string>;
  created_at: string;
}

export interface DashboardStats {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  active: number;
  remediated: number;
  total_agents: number;
  online_agents: number;
  trend: Array<{ hour: number; count: number }>;
  mitre_breakdown: Record<string, number>;
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  tenant_id: string;
}
