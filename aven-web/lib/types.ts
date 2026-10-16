export type Role = "biller" | "manager" | "admin";

// Higher number = more permissions. Mirrors ROLE_RANK in the API.
// The API always enforces permissions; this only decides what to show.
export const ROLE_RANK: Record<Role, number> = { biller: 1, manager: 2, admin: 3 };

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  org_id: string;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
}

export interface Me {
  user: User;
  organization: Organization;
}

export interface Practice {
  id: string;
  name: string;
  specialty: string | null;
  created_at: string;
}

export interface AuditEntry {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

/** Result of a form submission handled by a server action. */
export interface FormState {
  error?: string;
  ok?: boolean;
}
