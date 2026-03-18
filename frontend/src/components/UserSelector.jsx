const allUsersOption = {
  id: "all",
  name: "All Users",
};

export default function UserSelector({
  users,
  selectedUser,
  onSelect,
  disabled = false,
}) {
  const options = [allUsersOption, ...(Array.isArray(users) ? users : [])];

  return (
    <div className="wrapped-user-selector" role="group" aria-label="Choose a user">
      {options.map((user) => {
        const isActive = selectedUser === user.id;

        return (
          <button
            key={user.id}
            type="button"
            className={`wrapped-user-pill ${isActive ? "is-active" : ""}`}
            onClick={() => onSelect(user.id)}
            aria-pressed={isActive}
            disabled={disabled}
          >
            {user.name}
          </button>
        );
      })}
    </div>
  );
}
