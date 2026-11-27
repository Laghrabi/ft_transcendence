import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/auth/Login.jsx";
import Register from "./pages/auth/Register.jsx";
import Dashboard from "./pages/dashboard/Dashboard.jsx";
import CasesList from "./pages/cases/CasesList.jsx";
import CreateCase from "./pages/cases/CreateCase.jsx";
// import MyTasks from "./pages/my-tasks/MyTasks.jsx";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/cases" element={<CasesList />} />
        <Route path="/cases/new" element={<CreateCase />} />
        <Route path="/my-tasks" element={<MyTasks />} />    
      </Routes>
    </BrowserRouter>
  );
}

export default App;