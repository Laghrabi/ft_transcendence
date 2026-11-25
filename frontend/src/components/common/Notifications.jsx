import { useEffect, useState } from "react";
import { getNotifications,
  markNotificationRead,
} from "../../api/notifications";
import "../../styles/Common.css";

export default function Notifications({
  showNotifications,
  setShowNotifications,
  notificationButton,
  notificationStatus,
  setNotificationStatus,
  notificationRetry,
  retryNotifications,
  readStatus,
  setReadStatus,
}) {
  const [notifications, setNotifications] = useState([]);

  const unreadCount = notifications.filter(
    (notification) => !notification.is_read
  ).length;

  const isLoadingNotifications = notificationStatus === "loading";

  const isSavingNotification =
    Object.values(readStatus).includes("saving");

  useEffect(() => {
    const controller = new AbortController();

    async function loadNotifications() {
      try {
        const data = await getNotifications({
          signal: controller.signal,
        });

        if (!controller.signal.aborted) {
          setNotifications(data.notifications);
          setNotificationStatus("ready");
        }
      } catch {
        if (!controller.signal.aborted) {
          setNotificationStatus("error");
        }
      }
    }

    loadNotifications();

    return () => controller.abort();
  }, [notificationRetry, setNotificationStatus]);

  async function handleMarkAsRead(id, button) {
    if (
      isLoadingNotifications ||
      readStatus[id] === "saving"
    ) return;

    setReadStatus((current) => ({
      ...current,
      [id]: "saving",
    }));

    try {
      const updated = await markNotificationRead(id);

      if (document.activeElement === button) {
        button.closest("section")?.focus({
          preventScroll: true,
        });
      }

      setNotifications((current) =>
        current.map((notification) =>
          notification.id === id ? updated : notification
        )
      );

      setReadStatus((current) => {
        const next = { ...current };
        delete next[id];
        return next;
      });
    } catch {
      setReadStatus((current) => ({
        ...current,
        [id]: "error",
      }));
    }
  }

  return (
    <div
      className="cf-notification-wrapper"
      onKeyDown={(event) => {
        if (
          event.key === "Escape" &&
          showNotifications
        ) {
          event.preventDefault();
          setShowNotifications(false);
          notificationButton.current?.focus();
        }
      }}
    >
      <button
        ref={notificationButton}
        type="button"
        className="cf-icon-button cf-notifications"
        aria-label={
          notificationStatus === "ready" ||
          notifications.length > 0
            ? `Notifications (${unreadCount} unread)`
            : "Notifications"
        }
        aria-expanded={showNotifications}
        aria-controls={
          showNotifications
            ? "cf-notification-panel"
            : undefined
        }
        onClick={() =>
          setShowNotifications((open) => !open)
        }
      >
        <span
          className="material-symbols-outlined"
          aria-hidden="true"
        >
          notifications
        </span>

        {unreadCount > 0 && (
          <span
            className="cf-notification-count"
            aria-hidden="true"
          >
            {unreadCount}
          </span>
        )}
      </button>

      {showNotifications && (
        <section
          className="cf-notification-panel"
          id="cf-notification-panel"
          aria-labelledby="cf-notification-title"
          tabIndex={-1}
        >
          <h3 id="cf-notification-title">
            Notifications
          </h3>

          {notificationStatus === "loading" && (
            <p role="status">
              Loading notifications…
            </p>
          )}

          {notificationStatus === "error" && (
            <div>
              <p role="alert">
                Could not load notifications.
                {notifications.length > 0 &&
                  " Showing the last loaded list."}
              </p>

              <button
                type="button"
                className="cf-small-button"
                disabled={isSavingNotification}
                onClick={(event) => {
                  event.currentTarget
                    .closest("section")
                    ?.focus({ preventScroll: true });

                  retryNotifications();
                }}
              >
                Retry
              </button>
            </div>
          )}

          {notificationStatus === "ready" &&
            notifications.length === 0 && (
              <p role="status">
                No notifications yet.
              </p>
            )}

          {notifications.length > 0 && (
            <ul className="cf-notification-list">
              {notifications.map(
                ({ id, message, is_read: isRead }) => (
                  <li
                    key={id}
                    className="cf-notification-item"
                  >
                    <p>{message}</p>

                    {isRead ? (
                      <small role="status">Read</small>
                    ) : (
                      <button
                        type="button"
                        className="cf-small-button"
                        aria-disabled={
                          isLoadingNotifications ||
                          readStatus[id] === "saving"
                        }
                        onClick={(event) =>
                          handleMarkAsRead(
                            id,
                            event.currentTarget
                          )
                        }
                      >
                        {readStatus[id] === "saving"
                          ? "Saving…"
                          : "Mark as read"}
                      </button>
                    )}

                    {readStatus[id] === "error" && (
                      <p role="alert">
                        Could not mark as read.
                        Try again.
                      </p>
                    )}
                  </li>
                )
              )}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
