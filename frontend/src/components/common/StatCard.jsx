import "../../styles/Common.css";

export default function StatCard({ label, icon, color, value, description, warning = false }) {
  const cardClass = warning ? "cf-stat-card cf-stat-warning" : "cf-stat-card";

  return (
    <article className={cardClass}>
      <div className="cf-stat-top">
        <span className="cf-stat-label">{label}</span>
        <span className={`cf-stat-icon ${color}`}>
          <span className="material-symbols-outlined">{icon}</span>
        </span>
      </div>

      <div className="cf-stat-value">
        <strong>{value}</strong>
      </div>

      <p>{description}</p>
    </article>
  );
}
