import { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from './components/ui/toaster';
import { TooltipProvider } from './components/ui/tooltip';
import NotFound from './pages/not-found';
import { Route, Switch, Router as WouterRouter } from 'wouter';
import { useHashLocation } from 'wouter/use-hash-location';
import { Home } from './pages/Home';
import { MemoryPage } from './pages/MemoryPage';
import { VisionPage } from './pages/VisionPage';
import { VoicePage } from './pages/VoicePage';
import { ToolsPage } from './pages/ToolsPage';
import { AgentsPage } from './pages/AgentsPage';
import { WorkflowsPage } from './pages/WorkflowsPage';
import { SettingsPage } from './pages/SettingsPage';

import { CompanionService } from './services/CompanionService';
import { getBaseUrl } from './lib/api';

const queryClient = new QueryClient();

function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />
      <Route path="/memory" component={MemoryPage} />
      <Route path="/vision" component={VisionPage} />
      <Route path="/voice" component={VoicePage} />
      <Route path="/tools" component={ToolsPage} />
      <Route path="/agents" component={AgentsPage} />
      <Route path="/workflows" component={WorkflowsPage} />
      <Route path="/settings" component={SettingsPage} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  const [hasKey, setHasKey] = useState(!!localStorage.getItem('JARVIS_API_KEY'));
  const [inputValue, setInputValue] = useState('');

  useEffect(() => {
    let companion: CompanionService | null = null;
    let isMounted = true;

    if (hasKey) {
      getBaseUrl().then((baseUrl) => {
        if (!isMounted) return;
        companion = new CompanionService(baseUrl || window.location.origin);
        companion.connect();
      });
    }

    return () => {
      isMounted = false;
      if (companion) {
        companion.disconnect();
      }
    };
  }, [hasKey]);

  const handleKeySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      localStorage.setItem('JARVIS_API_KEY', inputValue.trim());
      setHasKey(true);
      window.location.reload();
    }
  };

  if (!hasKey) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100vh', backgroundColor: '#060c18', color: 'white', fontFamily: 'sans-serif', gap: '1rem' }}>
        <div style={{ padding: '2rem', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '1rem', border: '1px solid rgba(255,255,255,0.1)', textAlign: 'center' }}>
          <h2 style={{ marginBottom: '1rem' }}>Authentication Required</h2>
          <p style={{ marginBottom: '1.5rem', color: '#a1a1aa' }}>Please enter your Jarvis Secret Key to access the system.</p>
          <form onSubmit={handleKeySubmit} style={{ display: 'flex', gap: '0.5rem' }}>
            <input 
              type="password" 
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Enter JARVIS_SECRET_KEY..."
              style={{ flex: 1, padding: '0.5rem 1rem', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.2)', backgroundColor: 'rgba(0,0,0,0.5)', color: 'white' }}
              autoFocus
            />
            <button type="submit" style={{ padding: '0.5rem 1rem', borderRadius: '0.5rem', backgroundColor: '#7c3aed', color: 'white', border: 'none', cursor: 'pointer' }}>
              Connect
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter hook={useHashLocation}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;