import { useState } from 'react'
import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Calls from './pages/Calls'
import CallDetail from './pages/CallDetail'
import Appointments from './pages/Appointments'
import AppointmentDetail from './pages/AppointmentDetail'
import Customers from './pages/Customers'
import CustomerProfile from './pages/CustomerProfile'
import CalendarPage from './pages/CalendarPage'
import KnowledgeBase from './pages/KnowledgeBase'
import Emails from './pages/Emails'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'
import Campaigns from './pages/Campaigns'
import CampaignCreate from './pages/CampaignCreate'
import CampaignDetail from './pages/CampaignDetail'

type NavItem = { path: string; label: string; icon: string; comingSoon?: boolean }

const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'Dashboard', icon: '◻' },
  { path: '/calls', label: 'Calls', icon: '◎' },
  { path: '/appointments', label: 'Appointments', icon: '◈' },
  { path: '/customers', label: 'Customers', icon: '◉' },
  { path: '/calendar', label: 'Calendar', icon: '▦' },
  { path: '/knowledge', label: 'Knowledge Base', icon: '◇' },
  { path: '/emails', label: 'Emails', icon: '◆' },
  { path: '/campaigns', label: 'Campaigns', icon: '▸' },
  { path: '/analytics', label: 'Analytics', icon: '▤' },
  { path: '/settings', label: 'Settings', icon: '⚙' },
]

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  return (
    <div className="app-layout">
      <button
        className="mobile-nav-toggle"
        onClick={() => setSidebarOpen(!sidebarOpen)}
      >
        ☰
      </button>

      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">R</div>
          <span className="sidebar-title">RUSBORN</span>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section-label">Platform</div>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `nav-item ${isActive && location.pathname === item.path ? 'active' : ''}`
              }
              onClick={() => setSidebarOpen(false)}
              end={item.path === '/'}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
              {item.comingSoon && (
                <span className="nav-badge coming-soon">Soon</span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="status-indicator">
            <span className="status-dot healthy" />
            Agent Online
          </div>
          <div className="status-indicator">
            <span className="status-dot healthy" />
            System Healthy
          </div>
        </div>
      </aside>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/calls" element={<Calls />} />
          <Route path="/calls/:id" element={<CallDetail />} />
          <Route path="/appointments" element={<Appointments />} />
          <Route path="/appointments/:id" element={<AppointmentDetail />} />
          <Route path="/customers" element={<Customers />} />
          <Route path="/customers/:id" element={<CustomerProfile />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/knowledge" element={<KnowledgeBase />} />
          <Route path="/emails" element={<Emails />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/campaigns" element={<Campaigns />} />
          <Route path="/campaigns/new" element={<CampaignCreate />} />
          <Route path="/campaigns/:id" element={<CampaignDetail />} />
        </Routes>
      </main>
    </div>
  )
}
