import React from 'react'
import { Routes, Route } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import HomePage from './pages/HomePage'

// Note: Invitation pages require manual fixing before they can be imported
// See PHASE2_SUMMARY.md for details on which pages need attention

function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<HomePage />} />
        {/* Invitation routes will be added after fixing JSX syntax errors */}
      </Route>
    </Routes>
  )
}

export default App
