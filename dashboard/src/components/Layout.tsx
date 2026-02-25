import { ReactNode, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  Home,
  FileText,
  Hammer,
  Users,
  Cpu,
  History,
  Menu,
  X,
  Activity,
  ChevronRight,
  Settings,
  Shield,
  ScrollText
} from 'lucide-react'
import { cn } from '@/utils'
import { useWebSocket } from '@/hooks'

interface LayoutProps {
  children: ReactNode
}

const navigation = [
  { name: 'Home', href: '/', icon: Home },
  { name: 'Plan', href: '/plan', icon: FileText },
  { name: 'Build', href: '/build', icon: Hammer },
  { name: 'Agents', href: '/agents', icon: Users },
  { name: 'Models', href: '/models', icon: Cpu },
  { name: 'Runs', href: '/runs', icon: History },
]

const systemNav = [
  { name: 'Settings', href: '/settings', icon: Settings },
  { name: 'Policy', href: '/policy', icon: Shield },
  { name: 'Logs', href: '/logs', icon: ScrollText },
]

export function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const { status: wsStatus } = useWebSocket()

  const isActive = (href: string) => {
    if (href === '/') return location.pathname === '/'
    return location.pathname.startsWith(href)
  }

  return (
    <div className="min-h-screen bg-dark-950">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-50 w-64 bg-dark-900 border-r border-dark-700 transform transition-transform duration-200 ease-in-out lg:translate-x-0",
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between h-16 px-4 border-b border-dark-700">
            <Link to="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
                <Activity className="w-5 h-5 text-white" />
              </div>
              <span className="text-lg font-bold gradient-text">Lantrn</span>
            </Link>
            <button
              className="lg:hidden p-1 rounded-lg hover:bg-dark-700 transition-colors"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Main Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto scrollbar-thin">
            <div className="text-xs font-semibold text-dark-500 uppercase tracking-wider px-3 mb-2">
              Main
            </div>
            {navigation.map((item) => {
              const Icon = item.icon
              const active = isActive(item.href)
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                    active
                      ? "bg-primary-600/20 text-primary-400 border border-primary-500/30"
                      : "text-dark-300 hover:bg-dark-800 hover:text-white"
                  )}
                  onClick={() => setSidebarOpen(false)}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.name}</span>
                  {active && <ChevronRight className="w-4 h-4 ml-auto" />}
                </Link>
              )
            })}
            
            <div className="text-xs font-semibold text-dark-500 uppercase tracking-wider px-3 mt-6 mb-2">
              System
            </div>
            {systemNav.map((item) => {
              const Icon = item.icon
              const active = isActive(item.href)
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                    active
                      ? "bg-primary-600/20 text-primary-400 border border-primary-500/30"
                      : "text-dark-300 hover:bg-dark-800 hover:text-white"
                  )}
                  onClick={() => setSidebarOpen(false)}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.name}</span>
                  {active && <ChevronRight className="w-4 h-4 ml-auto" />}
                </Link>
              )
            })}
          </nav>

          {/* WebSocket Status */}
          <div className="p-4 border-t border-dark-700">
            <div className="flex items-center gap-2 text-sm">
              <div className={cn(
                "w-2 h-2 rounded-full",
                wsStatus === 'connected' ? "bg-green-500" :
                wsStatus === 'connecting' ? "bg-yellow-500 animate-pulse" :
                "bg-red-500"
              )} />
              <span className="text-dark-400">
                {wsStatus === 'connected' ? 'Connected' :
                 wsStatus === 'connecting' ? 'Connecting...' :
                 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="sticky top-0 z-30 h-16 bg-dark-900/80 backdrop-blur-md border-b border-dark-700">
          <div className="flex items-center justify-between h-full px-4">
            <button
              className="lg:hidden p-2 rounded-lg hover:bg-dark-700 transition-colors"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="w-5 h-5" />
            </button>
            
            <div className="flex items-center gap-4">
              <h1 className="text-lg font-semibold text-white hidden sm:block">
                {navigation.find(n => isActive(n.href))?.name || 
                 systemNav.find(n => isActive(n.href))?.name || 'Dashboard'}
              </h1>
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-dark-800 rounded-lg border border-dark-700">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-sm text-dark-300">System Active</span>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 md:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  )
}

export default Layout
