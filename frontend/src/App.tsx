import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from '@components/navigation/Layout';
import { Home } from '@pages/Home';
import { Conversation } from '@pages/Conversation';
import { Settings } from '@pages/Settings';
import { AuthCallback } from '@pages/AuthCallback';

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/conversation" element={<Conversation />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;