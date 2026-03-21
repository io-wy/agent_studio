import { useState, useEffect } from 'react';
import { apiService, Tenant, Project } from './api';
import './App.css';

function App() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [newTenantName, setNewTenantName] = useState('');
  const [newProjectName, setNewProjectName] = useState('');

  useEffect(() => {
    loadTenants();
  }, []);

  useEffect(() => {
    if (selectedTenant) {
      loadProjects(selectedTenant);
    }
  }, [selectedTenant]);

  const loadTenants = async () => {
    setLoading(true);
    try {
      const data = await apiService.getTenants();
      setTenants(data);
      if (data.length > 0 && !selectedTenant) {
        setSelectedTenant(data[0].id);
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const loadProjects = async (tenantId: string) => {
    try {
      const data = await apiService.getProjects(tenantId);
      setProjects(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateTenant = async () => {
    if (!newTenantName) return;
    try {
      await apiService.createTenant({ name: newTenantName });
      setNewTenantName('');
      loadTenants();
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateProject = async () => {
    if (!newProjectName || !selectedTenant) return;
    try {
      await apiService.createProject({
        tenant_id: selectedTenant,
        name: newProjectName
      });
      setNewProjectName('');
      loadProjects(selectedTenant);
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteTenant = async (id: string) => {
    try {
      await apiService.deleteTenant(id);
      if (selectedTenant === id) {
        setSelectedTenant(null);
        setProjects([]);
      }
      loadTenants();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🤖 Agent Studio</h1>
      </header>

      <main className="main">
        <section className="section">
          <h2>Tenants</h2>
          <div className="create-form">
            <input
              type="text"
              placeholder="New tenant name"
              value={newTenantName}
              onChange={(e) => setNewTenantName(e.target.value)}
            />
            <button onClick={handleCreateTenant}>Create Tenant</button>
          </div>
          <div className="list">
            {loading ? <p>Loading...</p> : tenants.map(tenant => (
              <div
                key={tenant.id}
                className={`card ${selectedTenant === tenant.id ? 'selected' : ''}`}
                onClick={() => setSelectedTenant(tenant.id)}
              >
                <h3>{tenant.name}</h3>
                <p>Status: {tenant.status}</p>
                <p>GPU Quota: {tenant.quota_gpuHours}h</p>
                <p>Storage: {tenant.quota_storage_gb}GB</p>
                <button
                  className="delete-btn"
                  onClick={(e) => { e.stopPropagation(); handleDeleteTenant(tenant.id); }}
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        </section>

        <section className="section">
          <h2>Projects</h2>
          {selectedTenant ? (
            <>
              <div className="create-form">
                <input
                  type="text"
                  placeholder="New project name"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                />
                <button onClick={handleCreateProject}>Create Project</button>
              </div>
              <div className="list">
                {projects.length === 0 ? (
                  <p>No projects yet</p>
                ) : projects.map(project => (
                  <div key={project.id} className="card">
                    <h3>{project.name}</h3>
                    <p>Status: {project.status}</p>
                    <p>Namespace: {project.namespace}</p>
                    <p>GPU Quota: {project.quota_gpuHours}h</p>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p>Select a tenant to view projects</p>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
