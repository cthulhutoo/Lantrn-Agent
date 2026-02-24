import { Routes, Route } from 'react-router-dom'
import { Layout } from '@/components'
import { Home, Plan, Build, Agents, Models, Runs } from '@/pages'

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
      </Routes>
    </Layout>
  )
}

export default App
