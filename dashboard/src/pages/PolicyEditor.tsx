import { useState } from 'react';
import { Shield, Plus, Trash2, Save, FileJson, AlertTriangle, CheckCircle } from 'lucide-react';

interface PolicyRule {
  id: string;
  name: string;
  type: 'file' | 'network' | 'execution' | 'api';
  action: 'allow' | 'deny';
  pattern: string;
  enabled: boolean;
}

const defaultPolicies: PolicyRule[] = [
  { id: '1', name: 'Deny system directories', type: 'file', action: 'deny', pattern: '/etc/**', enabled: true },
  { id: '2', name: 'Allow temp workspace', type: 'file', action: 'allow', pattern: '/tmp/**', enabled: true },
  { id: '3', name: 'Deny sensitive paths', type: 'file', action: 'deny', pattern: '/root/**', enabled: true },
  { id: '4', name: 'Deny external network', type: 'network', action: 'deny', pattern: '*', enabled: false },
  { id: '5', name: 'Allow localhost', type: 'network', action: 'allow', pattern: '127.0.0.1', enabled: true },
];

export default function PolicyEditor() {
  const [policies, setPolicies] = useState<PolicyRule[]>(defaultPolicies);
  const [selectedPolicy, setSelectedPolicy] = useState<PolicyRule | null>(null);
  const [saving, setSaving] = useState(false);
  const [jsonView, setJsonView] = useState(false);

  const handleAdd = () => {
    const newPolicy: PolicyRule = {
      id: Date.now().toString(),
      name: 'New Policy Rule',
      type: 'file',
      action: 'allow',
      pattern: '/path/**',
      enabled: true,
    };
    setPolicies([...policies, newPolicy]);
    setSelectedPolicy(newPolicy);
  };

  const handleDelete = (id: string) => {
    setPolicies(policies.filter(p => p.id !== id));
    if (selectedPolicy?.id === id) setSelectedPolicy(null);
  };

  const handleSave = async () => {
    setSaving(true);
    await new Promise(resolve => setTimeout(resolve, 800));
    setSaving(false);
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'file': return 'bg-blue-500/20 text-blue-400';
      case 'network': return 'bg-green-500/20 text-green-400';
      case 'execution': return 'bg-purple-500/20 text-purple-400';
      case 'api': return 'bg-orange-500/20 text-orange-400';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  };

  const updatePolicy = (id: string, updates: Partial<PolicyRule>) => {
    const updated = policies.map(p => p.id === id ? { ...p, ...updates } : p);
    setPolicies(updated);
    if (selectedPolicy?.id === id) {
      setSelectedPolicy({ ...selectedPolicy, ...updates });
    }
  };

  const jsonOutput = JSON.stringify(
    policies.reduce((acc, p) => {
      acc[p.name.toLowerCase().replace(/\s+/g, '_')] = {
        type: p.type,
        action: p.action,
        pattern: p.pattern,
        enabled: p.enabled,
      };
      return acc;
    }, {} as Record<string, unknown>),
    null,
    2
  );

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Shield className="text-purple-400" size={28} />
          <h1 className="text-2xl font-bold text-white">Policy Editor</h1>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={() => setJsonView(!jsonView)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              jsonView ? 'bg-purple-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            <FileJson size={18} />
            <span>{jsonView ? 'Editor View' : 'JSON View'}</span>
          </button>
          
          <button
            onClick={handleAdd}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
          >
            <Plus size={18} />
            <span>Add Rule</span>
          </button>
        </div>
      </div>

      {jsonView ? (
        <div className="bg-gray-900 rounded-xl p-6">
          <pre className="text-green-400 font-mono text-sm overflow-auto">
            {jsonOutput}
          </pre>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-6">
          {/* Policy List */}
          <div className="col-span-1 bg-gray-800 rounded-xl p-4 space-y-3">
            <h2 className="text-lg font-semibold text-white mb-4">Policy Rules</h2>
            
            {policies.map((policy) => (
              <div
                key={policy.id}
                onClick={() => setSelectedPolicy(policy)}
                className={`p-4 rounded-lg cursor-pointer transition-all ${
                  selectedPolicy?.id === policy.id
                    ? 'bg-purple-600/30 border border-purple-500'
                    : 'bg-gray-700/50 hover:bg-gray-700 border border-transparent'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-white font-medium">{policy.name}</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(policy.id); }}
                    className="text-red-400 hover:text-red-300"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs ${getTypeColor(policy.type)}`}>
                    {policy.type}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-xs ${policy.action === 'allow' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                    {policy.action}
                  </span>
                  {policy.enabled ? (
                    <CheckCircle size={14} className="text-green-400" />
                  ) : (
                    <AlertTriangle size={14} className="text-yellow-400" />
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Policy Editor */}
          <div className="col-span-2 bg-gray-800 rounded-xl p-6">
            {selectedPolicy ? (
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Rule Name</label>
                  <input
                    type="text"
                    value={selectedPolicy.name}
                    onChange={(e) => updatePolicy(selectedPolicy.id, { name: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Type</label>
                    <select
                      value={selectedPolicy.type}
                      onChange={(e) => updatePolicy(selectedPolicy.id, { type: e.target.value as PolicyRule['type'] })}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500"
                    >
                      <option value="file">File Access</option>
                      <option value="network">Network</option>
                      <option value="execution">Execution</option>
                      <option value="api">API Call</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Action</label>
                    <select
                      value={selectedPolicy.action}
                      onChange={(e) => updatePolicy(selectedPolicy.id, { action: e.target.value as PolicyRule['action'] })}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500"
                    >
                      <option value="allow">Allow</option>
                      <option value="deny">Deny</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Pattern</label>
                  <input
                    type="text"
                    value={selectedPolicy.pattern}
                    onChange={(e) => updatePolicy(selectedPolicy.id, { pattern: e.target.value })}
                    placeholder="/path/** or 192.168.1.0/24"
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-purple-500 font-mono"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium text-gray-300">Enabled</label>
                    <p className="text-xs text-gray-500">Rule is active when enabled</p>
                  </div>
                  <button
                    onClick={() => updatePolicy(selectedPolicy.id, { enabled: !selectedPolicy.enabled })}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      selectedPolicy.enabled ? 'bg-purple-600' : 'bg-gray-700'
                    }`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      selectedPolicy.enabled ? 'translate-x-6' : 'translate-x-1'
                    }`} />
                  </button>
                </div>

                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 text-white rounded-lg transition-colors"
                >
                  <Save size={18} />
                  <span>{saving ? 'Saving...' : 'Save Policy'}</span>
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                <Shield size={48} className="mb-4 opacity-50" />
                <p>Select a policy rule to edit</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
