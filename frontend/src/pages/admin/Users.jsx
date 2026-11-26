import Sidebar from "../../components/common/Sidebar";
import Topbar from "../../components/common/Topbar";
import StatCard from "../../components/common/StatCard";

import "../../styles/Common.css";
import "../../styles/Dashboard.css";
import "../../styles/Users.css";

const staffMembers = [
    {
        id: 1,
        name: "Marcus Vance",
        email: "marcus@hospital.com",
        initials: "MV",
        profession: "Doctor",
        is_active: true,
        is_department_admin: true,
    },
    {
        id: 2,
        name: "Sarah Chen",
        email: "sarah@hospital.com",
        initials: "SC",
        profession: "Nurse",
        is_active: true,
        is_department_admin: false,
    },
    {
        id: 3,
        name: "Tariq Khan",
        email: "tariq@hospital.com",
        initials: "TK",
        profession: "Doctor",
        is_active: false,
        is_department_admin: false,
    },
];

function Users() {
    return (
        <div className="cf-dashboard">
            <Sidebar />

            <div className="cf-page">
                <Topbar />

                <main className="cf-main">
                    <section className="cf-hero">
                        <div className="cf-hero-copy">
                            <h1>Users Management</h1>
                            <p>Manage hospital staff accounts.</p>
                        </div>
                    </section>

                    <section className="cf-stats">
                        <StatCard
                            label="TOTAL ACTIVE STAFF"
                            icon="groups"
                            color="green"
                            value="—"
                            description="Data unavailable"
                        />
                    </section>

                    <section className="users-directory">
                        <h2>Staff Directory</h2>

                        <table className="users-table">
                            <thead>
                                <tr>
                                    <th>Staff Member</th>
                                    <th>Role</th>
                                    <th>Activity</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>

                            <tbody>
                                {staffMembers.map((staff) => (
                                    <tr key={staff.id}>
                                        <td>
                                            <div className="users-staff">
                                                <div className="users-avatar">
                                                    {staff.initials}
                                                </div>

                                                <div className="users-staff-info">
                                                    <span className="users-staff-name">
                                                        {staff.name}
                                                    </span>

                                                    <span className="users-staff-email">
                                                        {staff.email}
                                                    </span>
                                                </div>
                                            </div>
                                        </td>

                                        <td>
                                            <div className="users-role">
                                                <span>{staff.profession}</span>

                                                {staff.is_department_admin && (
                                                    <span className="users-admin-badge">
                                                        Administrator
                                                    </span>
                                                )}
                                            </div>
                                        </td>

                                        <td>
                                            <span
                                                className={
                                                    staff.is_active
                                                        ? "users-activity users-active"
                                                        : "users-activity users-inactive"
                                                }
                                            >
                                                {staff.is_active ? "Active" : "Inactive"}
                                            </span>
                                        </td>

                                        <td>
                                            <button type="button">⋯</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </section>
                </main>
            </div>
        </div>
    );
}

export default Users;