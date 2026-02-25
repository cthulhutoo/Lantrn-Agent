import { Routes, Route } from 'react-router-dom'
import { Layout } from '@/components'
import { Home, Plan, Build, Agents, Models, Runs, Settings, PolicyEditor, Logs } from '@/pages'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/plan" element={<Plan />} />
        <Route path="/build" element={<Build />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/models" element={<Models />} />
        <Route path="/runs" element={<Runs />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/policy" element={<PolicyEditor />} />
        <Route path="/logs" element={<Logs />} />
      </Routes>
    </Layout>
  )
}

export default App
