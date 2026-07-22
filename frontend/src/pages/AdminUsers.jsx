import { useEffect, useState } from "react";
import DashboardLayout from "@/components/app/DashboardLayout";
import api from "@/lib/api";
import StatusBadge from "@/components/app/StatusBadge";

export default function AdminUsers() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/admin/users").then(({ data }) => setRows(data)).catch(() => {}); }, []);
  return (
    <DashboardLayout title="Users" subtitle="Everyone with an account on PMC Managers.">
      <div className="border overflow-x-auto">
        <table className="w-full text-sm pmc-table" data-testid="admin-users-table">
          <thead>
            <tr className="border-b bg-muted/30">
              <Th>Name</Th><Th>Email</Th><Th>Role</Th><Th>Vendor status</Th><Th>Joined</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((u) => (
              <tr key={u.id} className="border-b hover:bg-muted/40 transition-colors">
                <Td>{u.name}</Td>
                <Td>{u.email}</Td>
                <Td><span className="pmc-label">{u.role}</span></Td>
                <Td>{u.role === "vendor" ? <StatusBadge status={u.vendor_status} /> : <span className="text-muted-foreground">—</span>}</Td>
                <Td className="font-mono text-xs">{u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DashboardLayout>
  );
}

function Th({ children }) { return <th className="text-left px-4 py-3 pmc-label border-b">{children}</th>; }
function Td({ children, className = "" }) { return <td className={`px-4 py-3 ${className}`}>{children}</td>; }
