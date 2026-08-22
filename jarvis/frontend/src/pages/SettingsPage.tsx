import { useState, useEffect } from 'react';
import { PageShell } from '../components/ui/PageShell';
import { PageHeader } from '../components/ui/PageHeader';
import { Settings, Key, Link as LinkIcon, Shield, Server, Cpu, Box, Database, Webhook, Fingerprint } from 'lucide-react';
import { FaGithub } from 'react-icons/fa';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { api, getBaseUrl } from '../lib/api';
import { useToast } from '../hooks/use-toast';

export function SettingsPage() {
  const { toast } = useToast();

  const [activeTab, setActiveTab] = useState<'security' | 'integrations' | 'plugins'>('security');
  
  const [keys, setKeys] = useState({
    opencode: '',
    nvidia: '',
    groq: '',
    gemini: '',
    jina: ''
  });
  
  const [integrations, setIntegrations] = useState<{
    google: {id: number, account_id: string, label?: string, scopes?: string, token_expires_at?: string, token_active?: boolean}[],
    notion: {id: number, account_id: string}[],
    github: {id: number, account_id: string}[],
    whatsapp: boolean,
    telegram: boolean
  }>({
    google: [],
    notion: [],
    github: [],
    whatsapp: false,
    telegram: false
  });

  const [plugins, setPlugins] = useState({
    github_token: '',
    homeassistant_url: '',
    eth_rpc_url: '',
    database_url: ''
  });

  const [system, setSystem] = useState({
    ai_tool_selector_enabled: true
  });

  const [loading, setLoading] = useState(true);

  const handleUpdatePlugin = async (key: string, value: string) => {
    try {
      await api.post('/api/settings/plugins', { [key]: value });
      toast({ title: 'API Key Saved', description: `Successfully updated ${key}.` });
    } catch (e) {
      toast({ title: 'Error', description: `Failed to update ${key}.`, variant: 'destructive' });
    }
  };


  const handleSystemToggle = async () => {
    const newValue = !system.ai_tool_selector_enabled;
    setSystem({...system, ai_tool_selector_enabled: newValue});
    try {
      await api.post('/api/settings/system', { ai_tool_selector_enabled: newValue });
      toast({ title: 'System Updated', description: 'Intelligent Tool Selector is now ' + (newValue ? 'enabled' : 'disabled') });
    } catch (e) {
      toast({ title: 'Error', description: 'Failed to update system settings.', variant: 'destructive' });
      setSystem({...system, ai_tool_selector_enabled: !newValue});
    }
  };


  useEffect(() => {
    async function fetchData() {
      try {
        const [keysRes, integrationsRes, pluginsRes, systemRes] = await Promise.all([
          api.get('/api/settings/keys').catch(() => ({ok: false, data: null})),
          api.get('/api/settings/integrations').catch(() => ({ok: false, data: null})),
          api.get('/api/settings/plugins').catch(() => ({ok: false, data: null})),
          api.get('/api/settings/system').catch(() => ({ok: false, data: null}))
        ]);
        
        if (keysRes.ok && keysRes.data) {
          setKeys({
            opencode: keysRes.data.opencode || '',
            nvidia: keysRes.data.nvidia || '',
            groq: keysRes.data.groq || '',
            gemini: keysRes.data.gemini || '',
            jina: keysRes.data.jina || ''
          });
        }
        
        if (integrationsRes.ok && integrationsRes.data) {
          setIntegrations(integrationsRes.data);
        }

        if (pluginsRes.ok && pluginsRes.data) {
          setPlugins(pluginsRes.data);
        }

        if (systemRes.ok && systemRes.data) {
          setSystem(systemRes.data);
        }
      } catch (e) {
        console.error("Failed to fetch settings", e);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  return (
    <PageShell>
      <PageHeader 
        title="System Settings" 
        description="Manage API keys, OAuth integrations, and security policies."
        icon={<Settings className="text-[var(--accent-cyan)]" size={24} />}
      />

      <div className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto w-full">
        {/* Tabs */}
        <div className="flex border-b border-[var(--border-subtle)] mb-6 overflow-x-auto whitespace-nowrap hide-scrollbar">
          <button
            onClick={() => setActiveTab('security')}
            className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 flex items-center gap-2
              ${activeTab === 'security' 
                ? 'border-[var(--accent-cyan)] text-[var(--accent-cyan)] bg-[rgba(0,212,255,0.05)]' 
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[rgba(255,255,255,0.02)]'
              }`}
          >
            <Key size={16} /> Security & Keys
          </button>
          <button
            onClick={() => setActiveTab('integrations')}
            className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 flex items-center gap-2
              ${activeTab === 'integrations' 
                ? 'border-[var(--accent-violet)] text-[var(--accent-violet)] bg-[rgba(168,85,247,0.05)]' 
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[rgba(255,255,255,0.02)]'
              }`}
          >
            <LinkIcon size={16} /> Integrations
          </button>
          <button
            onClick={() => setActiveTab('plugins')}
            className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 flex items-center gap-2
              ${activeTab === 'plugins' 
                ? 'border-yellow-400 text-yellow-400 bg-yellow-400/5' 
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[rgba(255,255,255,0.02)]'
              }`}
          >
            <Box size={16} /> Plugins & Tools
          </button>
        </div>

        {/* Security Tab */}
        {activeTab === 'security' && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            
            {/* Core System */}
            <div className="bg-[rgba(255,255,255,0.02)] border border-[var(--border-subtle)] rounded-lg p-6">
              <div className="flex items-center gap-3 mb-4">
                <Settings className="text-[var(--accent-cyan)]" size={20} />
                <h3 className="text-lg font-medium">Core System Settings</h3>
              </div>
              <div className="flex items-center justify-between p-4 bg-[#0B0F19] border border-[var(--border-subtle)] rounded-lg">
                <div>
                  <h4 className="text-sm font-semibold text-white mb-1">Intelligent Tool Selector</h4>
                  <p className="text-xs text-[var(--text-muted)]">Dynamically filters the tool context to optimize LLM performance and save tokens.</p>
                </div>
                <button 
                  onClick={handleSystemToggle}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${system.ai_tool_selector_enabled ? 'bg-[var(--accent-cyan)]' : 'bg-zinc-700'}`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${system.ai_tool_selector_enabled ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
              </div>
            </div>

            {/* Primary AI Providers */}
            <div className="bg-[rgba(255,255,255,0.02)] border border-[var(--border-subtle)] rounded-lg p-6">
              <div className="flex items-center gap-3 mb-4">
                <Shield className="text-[var(--accent-cyan)]" size={20} />
                <h3 className="text-lg font-medium">Provider API Keys</h3>
              </div>
              <p className="text-sm text-[var(--text-muted)] mb-6">Keys are encrypted at rest using Fernet AES encryption.</p>
              
              <div className="space-y-4">
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">OpenCode</label>
                  <div className="flex gap-2">
                    <Input 
                      type="password" 
                      value={keys.opencode} 
                      placeholder={loading ? "Loading..." : "sk-..."}
                      readOnly 
                      className="bg-[#0B0F19] font-mono" 
                    />
                    <Button variant="outline">Update</Button>
                  </div>
                </div>


                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">Nvidia NIM</label>
                  <div className="flex gap-2">
                    <Input 
                      type="password" 
                      value={keys.nvidia} 
                      placeholder={loading ? "Loading..." : "nvapi-..."}
                      readOnly 
                      className="bg-[#0B0F19] font-mono" 
                    />
                    <Button variant="outline">Update</Button>
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">Groq</label>
                  <div className="flex gap-2">
                    <Input 
                      type="password" 
                      value={keys.groq} 
                      placeholder={loading ? "Loading..." : "gsk-..."}
                      readOnly 
                      className="bg-[#0B0F19] font-mono" 
                    />
                    <Button variant="outline">Update</Button>
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">Google Gemini</label>
                  <div className="flex gap-2">
                    <Input 
                      type="password" 
                      value={keys.gemini} 
                      placeholder={loading ? "Loading..." : "AI-..."}
                      readOnly 
                      className="bg-[#0B0F19] font-mono" 
                    />
                    <Button variant="outline">Update</Button>
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">Jina AI</label>
                  <div className="flex gap-2">
                    <Input 
                      type="password" 
                      value={keys.jina} 
                      placeholder={loading ? "Loading..." : "jina_..."}
                      readOnly 
                      className="bg-[#0B0F19] font-mono" 
                    />
                    <Button variant="outline">Update</Button>
                  </div>
                </div>
              </div>
            </div>

          </div>
        )}

        {/* Integrations Tab */}
        {activeTab === 'integrations' && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
              
              {/* Google Workspace */}
              <div className="bg-[rgba(255,255,255,0.02)] border border-[var(--border-subtle)] rounded-lg p-6 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="text-lg font-medium flex items-center gap-2">
                      <div className="w-8 h-8 rounded bg-white flex items-center justify-center p-1.5">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg" alt="Google" />
                      </div>
                      Google Workspace
                    </h3>
                  </div>
                  <p className="text-sm text-[var(--text-muted)] mb-4">Access Gmail, Calendar, and Drive documents autonomously.</p>
                  
                  {integrations.google && integrations.google.length > 0 && (
                    <div className="flex flex-col gap-3 mb-4">
                      {integrations.google.map(acc => (
                        <div key={acc.id} className="flex flex-col gap-2 bg-[rgba(0,0,0,0.2)] p-3 rounded border border-[var(--border-subtle)]">
                          <div className="flex justify-between items-center">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-white">{acc.account_id}</span>
                              {acc.label && (
                                <span className="px-2 py-0.5 text-xs bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded">
                                  {acc.label}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-1">
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                className="h-6 text-xs text-gray-400 hover:text-white"
                                onClick={async () => {
                                  const newLabel = window.prompt("Enter label for this account (e.g., 'Work', 'Personal'):", acc.label || "");
                                  if (newLabel !== null) {
                                    try {
                                      await api.patch(`/api/oauth/google/${acc.account_id}`, { label: newLabel });
                                      const res = await api.get('/api/settings/integrations');
                                      if (res.ok && res.data) setIntegrations(res.data);
                                      toast({ title: 'Label Updated', description: 'Account label saved.' });
                                    } catch (e) {
                                      toast({ title: 'Error', description: 'Failed to update label.', variant: 'destructive' });
                                    }
                                  }
                                }}
                              >
                                Label
                              </Button>
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                className="h-6 text-xs text-gray-400 hover:text-white"
                                onClick={async () => {
                                  try {
                                    await api.post(`/api/oauth/google/${acc.account_id}/refresh`, {});
                                    const res = await api.get('/api/settings/integrations');
                                    if (res.ok && res.data) setIntegrations(res.data);
                                    toast({ title: 'Token Refreshed', description: 'Successfully refreshed access token.' });
                                  } catch (e) {
                                    toast({ title: 'Refresh Failed', description: 'Could not refresh token. You may need to reconnect.', variant: 'destructive' });
                                  }
                                }}
                              >
                                Refresh
                              </Button>
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                className="h-6 text-xs text-red-400 hover:text-red-300 hover:bg-red-900/20"
                                onClick={async () => {
                                  if (window.confirm(`Disconnect Google account ${acc.account_id}?`)) {
                                    try {
                                      await api.delete(`/api/oauth/google/${acc.account_id}`);
                                      const res = await api.get('/api/settings/integrations');
                                      if (res.ok && res.data) setIntegrations(res.data);
                                      toast({ title: 'Account Disconnected', description: 'Successfully removed Google account.' });
                                    } catch (e) {
                                      toast({ title: 'Error', description: 'Failed to disconnect account.', variant: 'destructive' });
                                    }
                                  }
                                }}
                              >
                                Disconnect
                              </Button>
                            </div>
                          </div>
                          <div className="flex flex-col gap-1 mt-1">
                            {acc.token_expires_at !== undefined && (
                              <div className="text-xs flex items-center gap-1">
                                <span className="text-gray-500">Token Status:</span>
                                {acc.token_active ? (
                                  <span className="text-green-400 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-green-400"></span> Active</span>
                                ) : (
                                  <span className="text-red-400 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-red-400"></span> Expired</span>
                                )}
                              </div>
                            )}
                            {acc.scopes && (
                              <div className="text-xs text-gray-500 truncate" title={acc.scopes}>
                                <span className="text-gray-500">Scopes:</span> {acc.scopes.split(' ').map(s => s.split('/').pop()).join(', ')}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <Button onClick={async () => {
                  const baseUrl = await getBaseUrl();
                  window.location.href = `${baseUrl}/api/oauth/login/google`;
                }} className="w-full bg-white text-black hover:bg-gray-200">
                  {integrations.google && integrations.google.length > 0 ? "Add Another Account" : "Connect to Google"}
                </Button>
              </div>

              {/* Notion */}
              <div className="bg-[rgba(255,255,255,0.02)] border border-[var(--border-subtle)] rounded-lg p-6 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="text-lg font-medium flex items-center gap-2">
                      <div className="w-8 h-8 rounded bg-white flex items-center justify-center p-1">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/4/45/Notion_app_logo.png" alt="Notion" />
                      </div>
                      Notion
                    </h3>
                  </div>
                  <p className="text-sm text-[var(--text-muted)] mb-4">Read/write to Notion databases and pages as Jarvis.</p>
                  
                  {integrations.notion && integrations.notion.length > 0 && (
                    <div className="flex flex-col gap-2 mb-4">
                      {integrations.notion.map(acc => (
                        <div key={acc.id} className="flex justify-between items-center bg-[rgba(0,0,0,0.2)] p-2 rounded border border-[var(--border-subtle)]">
                          <span className="text-sm text-gray-300">{acc.account_id}</span>
                          <Button variant="ghost" size="sm" className="h-6 text-xs text-red-400 hover:text-red-300 hover:bg-red-900/20">Disconnect</Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <Button onClick={async () => {
                  const baseUrl = await getBaseUrl();
                  window.location.href = `${baseUrl}/api/oauth/login/notion`;
                }} className="w-full bg-white text-black hover:bg-gray-200">
                  {integrations.notion && integrations.notion.length > 0 ? "Add Another Workspace" : "Connect to Notion"}
                </Button>
              </div>

              {/* GitHub */}
              <div className="bg-[rgba(255,255,255,0.02)] border border-[var(--border-subtle)] rounded-lg p-6 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="text-lg font-medium flex items-center gap-2">
                      <FaGithub size={24} /> GitHub
                    </h3>
                  </div>
                  <p className="text-sm text-[var(--text-muted)] mb-4">Automate pull requests, issues, and CI/CD pipelines.</p>
                  
                  {integrations.github && integrations.github.length > 0 && (
                    <div className="flex flex-col gap-2 mb-4">
                      {integrations.github.map(acc => (
                        <div key={acc.id} className="flex justify-between items-center bg-[rgba(0,0,0,0.2)] p-2 rounded border border-[var(--border-subtle)]">
                          <span className="text-sm text-gray-300">@{acc.account_id}</span>
                          <Button variant="ghost" size="sm" className="h-6 text-xs text-red-400 hover:text-red-300 hover:bg-red-900/20">Disconnect</Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <Button onClick={async () => {
                  const baseUrl = await getBaseUrl();
                  window.location.href = `${baseUrl}/api/oauth/login/github`;
                }} className="w-full bg-[#2da44e] text-white hover:bg-[#2c974b]">
                  {integrations.github && integrations.github.length > 0 ? "Add Another Account" : "Connect to GitHub"}
                </Button>
              </div>


              {/* WhatsApp */}
              <div className="bg-[rgba(255,255,255,0.02)] border border-[var(--border-subtle)] rounded-lg p-6 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="text-lg font-medium flex items-center gap-2">
                      <div className="w-8 h-8 rounded bg-[#25D366] flex items-center justify-center p-1.5">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" alt="WhatsApp" className="filter brightness-0 invert" />
                      </div>
                      WhatsApp Bridge
                    </h3>
                    {integrations.whatsapp && (
                      <span className="px-2 py-1 text-xs font-medium bg-[rgba(34,197,94,0.1)] text-green-400 rounded-full">Connected</span>
                    )}
                  </div>
                  <p className="text-sm text-[var(--text-muted)] mb-4">Chat with Jarvis via WhatsApp using Twilio API.</p>
                </div>
                {integrations.whatsapp ? (
                  <Button variant="outline" className="w-full text-red-400 border-red-900/30 hover:bg-red-900/10">Disconnect</Button>
                ) : (
                  <Button className="w-full bg-[#25D366] text-white hover:bg-[#20b858]">Configure Twilio</Button>
                )}
              </div>

              {/* Telegram */}
              <div className="bg-[rgba(255,255,255,0.02)] border border-[var(--border-subtle)] rounded-lg p-6 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="text-lg font-medium flex items-center gap-2">
                      <div className="w-8 h-8 rounded bg-[#26A5E4] flex items-center justify-center p-1">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" alt="Telegram" />
                      </div>
                      Telegram Bot
                    </h3>
                    {integrations.telegram && (
                      <span className="px-2 py-1 text-xs font-medium bg-[rgba(34,197,94,0.1)] text-green-400 rounded-full">Connected</span>
                    )}
                  </div>
                  <p className="text-sm text-[var(--text-muted)] mb-4">Access your Jarvis assistant directly from Telegram.</p>
                </div>
                {integrations.telegram ? (
                  <Button variant="outline" className="w-full text-red-400 border-red-900/30 hover:bg-red-900/10">Disconnect</Button>
                ) : (
                  <Button className="w-full bg-[#26A5E4] text-white hover:bg-[#2094ce]">Add Bot Token</Button>
                )}
              </div>

            </div>

          </div>
        )}

        {/* Plugins Tab */}
        {activeTab === 'plugins' && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
              
              <div className="bg-[rgba(255,255,255,0.02)] border border-[var(--border-subtle)] rounded-lg p-6 flex flex-col gap-4">
                <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] pb-3 mb-2">
                  <Database className="text-green-400" size={18} />
                  <h3 className="text-lg font-medium">Database (SQL)</h3>
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">Database URL</label>
                  <div className="flex gap-2">
                    <Input type="text" value={plugins.database_url} onChange={(e) => setPlugins({...plugins, database_url: e.target.value})} className="bg-[#0B0F19] font-mono" placeholder="postgres://..." />
                    <Button variant="outline" onClick={() => handleUpdatePlugin("database_url", plugins.database_url)}>Save</Button>
                  </div>
                </div>
              </div>


              <div className="bg-[rgba(255,255,255,0.02)] border border-[var(--border-subtle)] rounded-lg p-6 flex flex-col gap-4">
                <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] pb-3 mb-2">
                  <Webhook className="text-orange-400" size={18} />
                  <h3 className="text-lg font-medium">Engineering</h3>
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">GitHub Token</label>
                  <div className="flex gap-2">
                    <Input type="text" value={plugins.github_token} onChange={(e) => setPlugins({...plugins, github_token: e.target.value})} className="bg-[#0B0F19] font-mono" placeholder="ghp_..." />
                    <Button variant="outline" onClick={() => handleUpdatePlugin("github_token", plugins.github_token)}>Save</Button>
                  </div>
                </div>
              </div>

              <div className="bg-[rgba(255,255,255,0.02)] border border-[var(--border-subtle)] rounded-lg p-6 flex flex-col gap-4">
                <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] pb-3 mb-2">
                  <Box className="text-yellow-400" size={18} />
                  <h3 className="text-lg font-medium">IoT & Web3</h3>
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">HomeAssistant URL</label>
                  <div className="flex gap-2">
                    <Input type="text" value={plugins.homeassistant_url} onChange={(e) => setPlugins({...plugins, homeassistant_url: e.target.value})} className="bg-[#0B0F19] font-mono" placeholder="http://..." />
                    <Button variant="outline" onClick={() => handleUpdatePlugin("homeassistant_url", plugins.homeassistant_url)}>Save</Button>
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">ETH RPC URL</label>
                  <div className="flex gap-2">
                    <Input type="text" value={plugins.eth_rpc_url} onChange={(e) => setPlugins({...plugins, eth_rpc_url: e.target.value})} className="bg-[#0B0F19] font-mono" placeholder="https://..." />
                    <Button variant="outline" onClick={() => handleUpdatePlugin("eth_rpc_url", plugins.eth_rpc_url)}>Save</Button>
                  </div>
                </div>
              </div>


              
            </div>
          </div>
        )}

      </div>
    </PageShell>
  );
}
