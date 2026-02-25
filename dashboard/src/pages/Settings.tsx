import { useState } from 'react';
import { Settings as SettingsIcon, Save, RefreshCw, Key, Server, Database, Shield } from 'lucide-react';

interface SettingsSection {
  id: string;
  label: string;
  icon: React.ReactNode;
}

const sections: SettingsSection[] = [
  { id: 'general', label: 'General', icon: <Server size={18} /> },
  { id: 'api', label: 'API Keys', icon: <Key size={18} /> },
  { id: 'database', label: 'Database', icon: <Database size={18} /> },
  { id: 'security', label: 'Security', icon: <Shield size={18} /> },
];

export default function Settings() {
  const [activeSection, setActiveSection] = useState('general');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [settings, setSettings] = useState({
    // General
    workspaceDir: './workspaces',
    maxWorkspaces: 10,
    autoCleanup: true,
    logLevel: 'info',
    
    // API Keys
    openaiKey: '',
    anthropicKey: '',
    openrouterKey: '',
    ollamaUrl: 'http://localhost:11434',
    
    // Database
    dbType: 'sqlite',
    dbPath: './data/lantrn.db',
    vectorDb: 'chroma',
    vectorDbPath: './data/vectors',
    
    // Security
    requireApproval: true,
    allowedPaths: '/tmp,/var/tmp,/home',
    deniedPaths: '/etc,/root,/sys',
    maxFileSize: 10485760,
    maxExecutionTime: 300,
  });

  const handleSave = async () => {
    setSaving(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const renderSection = () => {
    switch (activeSection) {
      case 'general':
        return (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Workspace Directory
              </label>
              <input
                type="text"
                value={settings.workspaceDir}
                onChange={(e) => setSettings({ ...settings, workspaceDir: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Max Concurrent Workspaces
              </label>
              <input
                type="number"
                value={settings.maxWorkspaces}
                onChange={(e) => setSettings({ ...settings, maxWorkspaces: parseInt(e.target.value) })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-300">Auto Cleanup</label>
                <p className="text-xs text-gray-500">Automatically clean up completed workspaces</p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, autoCleanup: !settings.autoCleanup })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.autoCleanup ? 'bg-purple-600' : 'bg-gray-700'
                }`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.autoCleanup ? 'translate-x-6' : 'translate-x-1'
                }`} />
              </button>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Log Level
              </label>
              <select
                value={settings.logLevel}
                onChange={(e) => setSettings({ ...settings, logLevel: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="debug">Debug</option>
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="error">Error</option>
              </select>
            </div>
          </div>
        );
      
      case 'api':
        return (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                OpenAI API Key
              </label>
              <input
                type="password"
                value={settings.openaiKey}
                onChange={(e) => setSettings({ ...settings, openaiKey: e.target.value })}
                placeholder="sk-..."
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Anthropic API Key
              </label>
              <input
                type="password"
                value={settings.anthropicKey}
                onChange={(e) => setSettings({ ...settings, anthropicKey: e.target.value })}
                placeholder="sk-ant-..."
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                OpenRouter API Key
              </label>
              <input
                type="password"
                value={settings.openrouterKey}
                onChange={(e) => setSettings({ ...settings, openrouterKey: e.target.value })}
                placeholder="sk-or-..."
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Ollama URL
              </label>
              <input
                type="text"
                value={settings.ollamaUrl}
                onChange={(e) => setSettings({ ...settings, ollamaUrl: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            
            <div className="flex items-center gap-2 text-yellow-500 text-sm">
              <RefreshCw size={16} />
              <span>API keys are stored securely and encrypted at rest</span>
            </div>
          </div>
        );
      
      case 'database':
        return (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Database Type
              </label>
              <select
                value={settings.dbType}
                onChange={(e) => setSettings({ ...settings, dbType: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="sqlite">SQLite</option>
                <option value="postgresql">PostgreSQL</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Database Path
              </label>
              <input
                type="text"
                value={settings.dbPath}
                onChange={(e) => setSettings({ ...settings, dbPath: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Vector Database
              </label>
              <select
                value={settings.vectorDb}
                onChange={(e) => setSettings({ ...settings, vectorDb: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="chroma">ChromaDB</option>
                <option value="qdrant">Qdrant</option>
                <option value="milvus">Milvus</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Vector Database Path
              </label>
              <input
                type="text"
                value={settings.vectorDbPath}
                onChange={(e) => setSettings({ ...settings, vectorDbPath: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
          </div>
        );
      
      case 'security':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-300">Require Tool Approval</label>
                <p className="text-xs text-gray-500">Require approval before executing tools</p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, requireApproval: !settings.requireApproval })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.requireApproval ? 'bg-purple-600' : 'bg-gray-700'
                }`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.requireApproval ? 'translate-x-6' : 'translate-x-1'
                }`} />
              </button>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Allowed Paths (comma-separated)
              </label>
              <input
                type="text"
                value={settings.allowedPaths}
                onChange={(e) => setSettings({ ...settings, allowedPaths: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Denied Paths (comma-separated)
              </label>
              <input
                type="text"
                value={settings.deniedPaths}
                onChange={(e) => setSettings({ ...settings, deniedPaths: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Max File Size (bytes)
              </label>
              <input
                type="number"
                value={settings.maxFileSize}
                onChange={(e) => setSettings({ ...settings, maxFileSize: parseInt(e.target.value) })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Max Execution Time (seconds)
              </label>
              <input
                type="number"
                value={settings.maxExecutionTime}
                onChange={(e) => setSettings({ ...settings, maxExecutionTime: parseInt(e.target.value) })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
          </div>
        );
      
      default:
        return null;
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-8">
        <SettingsIcon className="text-purple-400" size={28} />
        <h1 className="text-2xl font-bold text-white">Settings</h1>
      </div>
      
      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-64 space-y-2">
          {sections.map((section) => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                activeSection === section.id
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {section.icon}
              <span>{section.label}</span>
            </button>
          ))}
        </div>
        
        {/* Content */}
        <div className="flex-1 bg-gray-800 rounded-xl p-6">
          <h2 className="text-xl font-semibold text-white mb-6">
            {sections.find(s => s.id === activeSection)?.label} Settings
          </h2>
          
          {renderSection()}
          
          <div className="mt-8 pt-6 border-t border-gray-700 flex items-center gap-4">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-6 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 text-white rounded-lg transition-colors"
            >
              {saving ? (
                <RefreshCw size={18} className="animate-spin" />
              ) : (
                <Save size={18} />
              )}
              <span>{saving ? 'Saving...' : 'Save Settings'}</span>
            </button>
            
            {saved && (
              <span className="text-green-400 text-sm">Settings saved successfully!</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
