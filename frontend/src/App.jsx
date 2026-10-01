import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";

import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import PostingsListPage from "./pages/PostingsListPage";
import PostingDetailPage from "./pages/PostingDetailPage";
import NewPostingPage from "./pages/NewPostingPage";
import MyApplicationsPage from "./pages/MyApplicationsPage";
import ReviewApplicationsPage from "./pages/ReviewApplicationsPage";
import ReviewPostingApplicantsPage from "./pages/ReviewPostingApplicantsPage";
import NotificationsPage from "./pages/NotificationsPage";
import LinkAnumatiPage from "./pages/LinkAnumatiPage";
import AgentsPage from "./pages/AgentsPage";

function Home() {
  const { user } = useAuth();
  return <Navigate to={user ? "/postings" : "/login"} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            <Route
              path="/postings"
              element={
                <ProtectedRoute>
                  <PostingsListPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/postings/new"
              element={
                <ProtectedRoute roles={["faculty", "institution_admin"]}>
                  <NewPostingPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/postings/:id"
              element={
                <ProtectedRoute>
                  <PostingDetailPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/my-applications"
              element={
                <ProtectedRoute roles={["student"]}>
                  <MyApplicationsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/review"
              element={
                <ProtectedRoute roles={["faculty", "institution_admin"]}>
                  <ReviewApplicationsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/review/:id"
              element={
                <ProtectedRoute roles={["faculty", "institution_admin"]}>
                  <ReviewPostingApplicantsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/anumati"
              element={
                <ProtectedRoute>
                  <LinkAnumatiPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/agents"
              element={
                <ProtectedRoute>
                  <AgentsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/notifications"
              element={
                <ProtectedRoute>
                  <NotificationsPage />
                </ProtectedRoute>
              }
            />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
