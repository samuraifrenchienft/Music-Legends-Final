import { Link, useLocation } from 'react-router-dom'

const TABS = [
  { path: '/',           icon: '🏠', label: 'Home'   },
  { path: '/daily',      icon: '🎁', label: 'Daily'  },
  { path: '/store',      icon: '🛒', label: 'Store'  },
  { path: '/market',     icon: '🏪', label: 'Market' },
  { path: '/trade',      icon: '🤝', label: 'Trade'  },
  { path: '/packs',      icon: '📦', label: 'Packs'  },
  { path: '/collection', icon: '🃏', label: 'Cards'  },
  { path: '/battle',     icon: '⚔️', label: 'Battle' },
]

export default function NavBar() {
  const { pathname } = useLocation()
  return (
    <nav style={{
      position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)',
      width: '100%', maxWidth: 480, display: 'flex',
      overflowX: 'auto',
      backgroundColor: '#1a1740', borderTop: '1px solid #6B2EBE',
      paddingBottom: 'env(safe-area-inset-bottom)',
      zIndex: 100,
    }}>
      {TABS.map(tab => (
        <Link key={tab.path} to={tab.path} style={{
          minWidth: 72, textAlign: 'center', padding: '8px 0',
          color: pathname === tab.path ? '#F4A800' : '#8888aa',
          textDecoration: 'none', fontSize: 11,
        }}>
          <div style={{ fontSize: 22 }}>{tab.icon}</div>
          {tab.label}
        </Link>
      ))}
    </nav>
  )
}
