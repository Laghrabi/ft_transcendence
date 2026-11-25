import "../../styles/Common.css";

export default function Topbar({ children }) {
  return (
    <header className="cf-topbar">

      {/* TODO: Enable search after integrating real task data. */}
      <div className="cf-search">
        <span
          className="material-symbols-outlined"
          aria-hidden="true"
        >
          search
        </span>

        <input
          type="search"
          placeholder="Search unavailable"
          aria-label="Search unavailable until task data is connected"
          disabled
        />
      </div>

      <div className="cf-topbar-right">

        {children}

        {/* TODO: Display real authenticated user information. */}
        <div className="cf-profile">
          <div className="cf-profile-text">
            <strong>Account</strong>
            <span>Profile unavailable</span>
          </div>

          <div className="cf-avatar" aria-hidden="true">
            <span className="material-symbols-outlined">
              person
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
