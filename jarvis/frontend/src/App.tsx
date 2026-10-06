import { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from './components/ui/toaster';
import { TooltipProvider } from './components/ui/tooltip';
import NotFound from './pages/not-found';
import { Route, Switch, Router as WouterRouter } from 'wouter';
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

// Custom robust hash location hook to handle query params and exact path matching safely
function useHashLocation() {
  const [loc, setLoc] = useState(() => {
    const hash = window.location.hash.replace(/^#/, '') || '/';
    return hash.split('?')[0]; // Strip query string for route matching
  });

  useEffect(() => {
    const handler = () => {
      const hash = window.location.hash.replace(/^#/, '') || '/';
      setLoc(hash.split('?')[0]);
    };
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  const navigate = (to: string) => { window.location.hash = to; };
  return [loc, navigate] as [string, (to: string) => void];
}

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
  const [location] = useHashLocation();
  const [hasKey, setHasKey] = useState(() => {
    try {
      return !!localStorage.getItem('JARVIS_API_KEY');
    } catch (e) {
      return false;
    }
  });
  const [inputValue, setInputValue] = useState('');



  useEffect(() => {
    let companion: CompanionService | null = null;
    let isMounted = true;

    if (true) {
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