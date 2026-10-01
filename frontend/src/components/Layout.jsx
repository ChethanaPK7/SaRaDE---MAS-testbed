import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

function NavItem({ to, children }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
          isActive
            ? "bg-navy-600 text-white"
            : "text-navy-700 hover:bg-navy-50"
        }`
      }
    >
      {children}
    </NavLink>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const isReviewer = user?.role === "faculty" || user?.role === "institution_admin";

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-navy-100 bg-paper-raised">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-md bg-navy-700 text-amber-400 font-display font-bold flex items-center justify-center text-sm">
              S
            </span>
            <span className="font-display text-lg font-semibold text-navy-900">
              SRIP
            </span>
          </Link>

          {user && (
            <nav className="flex items-center gap-1">
              <NavItem to="/postings">Postings</NavItem>
              {!isReviewer && <NavItem to="/my-applications">My applications</NavItem>}
              {isReviewer && <NavItem to="/review">Review</NavItem>}
              {isReviewer && <NavItem to="/postings/new">New posting</NavItem>}
              <NavItem to="/anumati">Anumati</NavItem>
              <NavItem to="/agents">AI Agents</NavItem>
              <NavItem to="/notifications">Notifications</NavItem>
            </nav>
          )}

          <div className="flex items-center gap-3">
            {user ? (
              <>
                <span className="text-sm text-ink/60 hidden sm:inline">
                  {user.first_name || user.username}
                  <span className="text-ink/40"> · {user.role.replace("_", " ")}</span>
                </span>
                <button
                  onClick={handleLogout}
                  className="text-sm font-medium text-rust-600 hover:text-rust-500"
                >
                  Log out
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-sm font-medium text-navy-700">
                  Log in
                </Link>
                <Link
                  to="/register"
                  className="text-sm font-medium bg-navy-700 text-white px-3 py-1.5 rounded-full"
                >
                  Sign up
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        <Outlet />
      </main>

      <footer className="border-t border-navy-100 py-4">
        <div className="max-w-6xl mx-auto px-6 text-xs text-ink/40">
          SaRaDE — Student Research & Development Exchange;
          document sharing runs through a linked Anumati locker.
        </div>
      </footer>
    </div>
  );
}
