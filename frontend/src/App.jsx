import { useEffect, useRef, useState } from 'react';
import './App.css';
import { Toaster, toast } from 'react-hot-toast';

const API_BASE = 'http://127.0.0.1:8000';
const PASSWORD_POLICY = 'Şifre en az 8 karakter olmalı; 1 büyük harf, 1 küçük harf, 1 rakam ve 1 özel karakter içermelidir.';

// --- CRDT MERGE FONKSİYONU (Popravljeno za brisanje) ---
const mergeTasks = (localTasks, incomingTasks) => {
  const localMap = new Map(localTasks.map(t => [t.id, t]));

  // Sada prolazimo SAMO kroz zadatke koji su zaista stigli sa backenda
  return incomingTasks.map(incoming => {
    if (localMap.has(incoming.id)) {
      const local = localMap.get(incoming.id);
      const merged = { ...local };

      // LWW (Last-Write-Wins) Mantığı
      if (incoming.title_updated_at > (local.title_updated_at || 0)) {
        merged.title = incoming.title;
        merged.title_updated_at = incoming.title_updated_at;
        merged.priority = incoming.priority;
        merged.status = incoming.status;
        merged.deadline = incoming.deadline;
        merged.assigned_to = incoming.assigned_to;
      }
      if (incoming.desc_updated_at > (local.desc_updated_at || 0)) {
        merged.description = incoming.description;
        merged.desc_updated_at = incoming.desc_updated_at;
      }
      
      merged.image_url = incoming.image_url;
      merged.comments = incoming.comments;
      return merged;
    } else {
      // Ako je zadatak potpuno nov, samo ga dodaj
      return incoming;
    }
  }).sort((a, b) => b.id - a.id);
};

function App() {
  const [currentView, setCurrentView] = useState('login');
  const [isDarkMode, setIsDarkMode] = useState(() => localStorage.getItem('theme') === 'dark');
  
  // Auth state
  const [loginIdentifier, setLoginIdentifier] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginShowPassword, setLoginShowPassword] = useState(false);
  const [loginError, setLoginError] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');
  const [regError, setRegError] = useState('');
  const [showRegPass, setShowRegPass] = useState(false);
  const [showConfirmPass, setShowConfirmPass] = useState(false);

  // Task state
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDesc, setTaskDesc] = useState('');
  const [taskPriority, setTaskPriority] = useState('Normal');
  const [taskStatus, setTaskStatus] = useState('To-Do');
  const [taskDeadline, setTaskDeadline] = useState('');
  const [taskAssignedTo, setTaskAssignedTo] = useState('');
  const [taskFile, setTaskFile] = useState(null);
  const [taskMessage, setTaskMessage] = useState({ text: '', type: '' });
  const [tasksList, setTasksList] = useState([]);
  const [commentDrafts, setCommentDrafts] = useState({});
  const socketRef = useRef(null);
  const [isWsConnected, setIsWsConnected] = useState(false);

  // Filters / search / stats (Person 2 - Week 2)
  const [filterPriority, setFilterPriority] = useState('All');
  const [filterStatus, setFilterStatus] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [stats, setStats] = useState(null);
  const importFileRef = useRef(null);

  // Profile & Edit State
  const [userData, setUserData] = useState(null);
  const [oldPass, setOldPass] = useState('');
  const [newPass, setNewPass] = useState('');
  const [confirmNewPass, setConfirmNewPass] = useState('');
  const [showOldPass, setShowOldPass] = useState(false);
  const [showNewPass, setShowNewPass] = useState(false);
  const [showConfirmNewPass, setShowConfirmNewPass] = useState(false);
  const [passMessage, setPassMessage] = useState({ text: '', type: '' });
  
  const [profileFile, setProfileFile] = useState(null);
  const [profileMessage, setProfileMessage] = useState({ text: '', type: '' });

  const [editingTaskId, setEditingTaskId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editPriority, setEditPriority] = useState('');
  const [editStatus, setEditStatus] = useState('In-Progress');
  const [editDeadline, setEditDeadline] = useState('');
  const [editAssignedTo, setEditAssignedTo] = useState('');

  const taskFileRef = useRef(null);
  const profileFileRef = useRef(null);

  const toggleTheme = () => setIsDarkMode((prev) => !prev);

  useEffect(() => {
    localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
    document.body.classList.toggle('dark-theme', isDarkMode);
  }, [isDarkMode]);

// LOGIN KONTROL 
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      fetchUserData().then(success => {
        if (success) {
          setCurrentView('dashboard');
        } else {
          localStorage.removeItem('token');
          setCurrentView('login');
        }
      });
    }
  }, []);

  const readError = async (res, fallback) => {
    try {
      const data = await res.json();
      if (Array.isArray(data?.detail)) {
        return data.detail.map((item) => (typeof item === 'string' ? item : item?.msg)).filter(Boolean).join('\n');
      }
      if (typeof data?.detail === 'string') return data.detail;
      return fallback;
    } catch { return fallback; }
  };

  const formatUrl = (path) => path ? `${API_BASE}${path.startsWith('/') ? path : `/${path}`}` : '';
  const authHeaders = () => {
    const token = localStorage.getItem('token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const getPasswordIssues = (password) => {
    const issues = [];
    if ((password || '').length < 8) issues.push('En az 8 karakter');
    if (!/[A-Z]/.test(password || '')) issues.push('1 büyük harf eksik');
    if (!/[a-z]/.test(password || '')) issues.push('1 küçük harf eksik');
    if (!/\d/.test(password || '')) issues.push('1 rakam eksik');
    if (!/[^A-Za-z0-9]/.test(password || '')) issues.push('1 özel karakter eksik');
    return issues;
  };

  const fetchUserData = async () => {
    const res = await fetch(`${API_BASE}/users/me`, { headers: authHeaders() });
    if (res.ok) {
      const data = await res.json();
      setUserData(data);
      return true;
    }
    if (res.status === 401) logout();
    return false;
  };

  const fetchTasks = async () => {
    const res = await fetch(`${API_BASE}/tasks`, { headers: authHeaders() });
    if (res.ok) {
      const data = await res.json();
      setTasksList((prev) => mergeTasks(prev, data));
      return true;
    }
    return false;
  };

  const fetchStats = async () => {
    const res = await fetch(`${API_BASE}/tasks/stats`, { headers: authHeaders() });
    if (res.ok) {
      setStats(await res.json());
      return true;
    }
    return false;
  };

  const fetchAll = async () => {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
      await Promise.all([fetchTasks(), fetchUserData(), fetchStats()]);
    } catch (e) {
      setTaskMessage({ text: 'Sunucuya bağlanılamadı.', type: 'error' });
    }
  };

  useEffect(() => {
    if (currentView === 'dashboard' || currentView === 'profile') void fetchAll();
  }, [currentView]);

  // Yeni Eklenen WebSocket useEffect'i
// Yeni Eklenen WebSocket useEffect'i
  useEffect(() => {
    if (currentView !== 'dashboard' && currentView !== 'profile') return;

    const wsUrl = API_BASE.replace('http', 'ws') + '/ws';
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log('WebSocket Bağlantısı Açıldı');
      setIsWsConnected(true);
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'update') {
          // Gelen mesajda bir 'action' varsa ve bu action 'task_changed' ise
          if (message.payload && message.payload.action === 'task_changed') {
              // Görevleri yenile
              fetchTasks();
              
              // Herhangi bir temada güzel görünen standart başarılı bildirimini göster
              toast.success('Bir görev güncellendi!', {
                  duration: 4000,
                  position: 'bottom-right',
              });
          }
        }
      } catch (e) {
        console.error('Mesaj işlenirken hata:', e);
      }
    };

    socket.onclose = () => {
      console.log('WebSocket Bağlantısı Kapatıldı');
      setIsWsConnected(false);
    };

    return () => {
      socket.close();
    };
  }, [currentView]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    if (!loginIdentifier.trim() || !loginPassword) {
      setLoginError('Kullanıcı adı/e-posta ve şifre zorunludur.');
      return;
    }
    const res = await fetch(`${API_BASE}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier: loginIdentifier.trim(), password: loginPassword }),
    });
    if (res.ok) {
      const data = await res.json();
      localStorage.setItem('token', data.access_token);
      setCurrentView('dashboard');
      return;
    }
    setLoginError(await readError(res, 'Giriş başarısız.'));
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setRegError('');
    if (!regUsername.trim() || !regEmail.trim() || !regPassword || !regConfirmPassword) {
      setRegError('Tüm alanlar zorunludur.'); return;
    }
    if (regPassword !== regConfirmPassword) {
      setRegError('Şifreler eşleşmiyor.'); return;
    }
    const issues = getPasswordIssues(regPassword);
    if (issues.length > 0) {
      setRegError(`${PASSWORD_POLICY}\n${issues.join('\n')}`); return;
    }
    const res = await fetch(`${API_BASE}/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: regUsername.trim(), email: regEmail.trim().toLowerCase(), password: regPassword }),
    });
    if (res.ok) { setCurrentView('login'); return; }
    setRegError(await readError(res, 'Kayıt başarısız.'));
  };

  // Yardımcı Fonksiyon: WebSocket üzerinden değişiklik bildirimi gönder
  const notifyTaskChange = () => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ action: "task_changed" }));
    }
  };

  const handleCreateTask = async (e) => {
    e.preventDefault();
    setTaskMessage({ text: '', type: '' });

    const formData = new FormData();
    formData.append('title', taskTitle.trim());
    formData.append('description', taskDesc.trim());
    formData.append('priority', taskPriority);
    formData.append('status', taskStatus);
    formData.append('deadline', taskDeadline);
    formData.append('assigned_to', taskAssignedTo.trim());
    formData.append('title_at', Date.now() / 1000);
    formData.append('desc_at', Date.now() / 1000);
    if (taskFile) formData.append('file', taskFile);

    const res = await fetch(`${API_BASE}/tasks`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    });
    if (res.ok) {
      setTaskTitle(''); setTaskDesc(''); setTaskDeadline(''); setTaskAssignedTo('');
      setTaskPriority('Normal'); setTaskStatus('To-Do'); setTaskFile(null);
      if (taskFileRef.current) taskFileRef.current.value = "";
      setTaskMessage({ text: 'Görev başarıyla kaydedildi.', type: 'success' });
      void fetchTasks();
      void fetchStats();
      notifyTaskChange();
    } else {
      const err = await readError(res, 'Görev kaydedilemedi.');
      setTaskMessage({ text: err, type: 'error' });
    }
  };

  const handleExportTasks = async () => {
    const res = await fetch(`${API_BASE}/tasks/export`, { headers: authHeaders() });
    if (!res.ok) { toast.error('Dışa aktarım başarısız'); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'tasks-export.json';
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
    toast.success('Görevler JSON olarak indirildi.');
  };

  const handleImportTasks = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      const items = Array.isArray(parsed) ? parsed : (parsed.tasks || []);
      const res = await fetch(`${API_BASE}/tasks/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ tasks: items }),
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(`${data.created} görev içe aktarıldı.`);
        void fetchTasks(); void fetchStats(); notifyTaskChange();
      } else {
        toast.error(await readError(res, 'İçe aktarım başarısız.'));
      }
    } catch {
      toast.error('Geçersiz JSON dosyası.');
    } finally {
      if (importFileRef.current) importFileRef.current.value = '';
    }
  };

  const handleUpdateTask = async (taskId, updatedData) => {
    const now = Date.now() / 1000;
    const finalData = {
      id: taskId,
      ...updatedData,
      title_updated_at: now,
      desc_updated_at: now
    };
    setTasksList((prev) => 
      prev.map((t) => (t.id === taskId ? { ...t, ...finalData } : t))
    );

    const res = await fetch(`${API_BASE}/tasks/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(finalData),
    });

    if (res.ok) {
      notifyTaskChange();
    } else {
      toast.error(await readError(res, 'Güncelleme başarısız.'));
    }
  };

  const handleMarkCompleted = async (task) => {
    const now = Date.now() / 1000;

    setTasksList((prev) => 
      prev.map((t) => (t.id === task.id ? { 
        ...t, 
        status: 'Completed', 
        title_updated_at: now,
        completed_at: new Date().toISOString() 
      } : t))
    );

    const res = await fetch(`${API_BASE}/tasks/${task.id}/complete`, {
      method: 'POST',
      headers: authHeaders(),
    });
    if (res.ok) {
      void fetchStats(); 
      notifyTaskChange();
      toast.success(`#${task.id} tamamlandı olarak işaretlendi.`);
    } else {
      toast.error(await readError(res, 'İşlem başarısız.'));
      void fetchTasks(); // Eğer hata olursa ekranı eski gerçek haline döndür
    }
  };
  const handleReopenTask = async (task) => {
    const now = Date.now() / 1000;

    setTasksList((prev) => 
      prev.map((t) => (t.id === task.id ? { 
        ...t, 
        status: 'In-Progress', 
        title_updated_at: now,
        completed_at: null 
      } : t))
    );

    const res = await fetch(`${API_BASE}/tasks/${task.id}/reopen`, {
      method: 'POST',
      headers: authHeaders(),
    });
    if (res.ok) {
      void fetchTasks();
      void fetchStats(); 
      notifyTaskChange();
      toast.success(`#${task.id} yeniden açıldı.`);
    } else {
      toast.error(await readError(res, 'İşlem başarısız.'));
      void fetchTasks(); // Hata olursa geri al
    }
  };

  const handleDeleteTask = async (taskId) => {
    const res = await fetch(`${API_BASE}/tasks/${taskId}`, { method: 'DELETE', headers: authHeaders() });
    if (res.ok) {
      void fetchTasks();
      void fetchStats();
      notifyTaskChange();
    }
  };

  const handleAddComment = async (taskId) => {
    const text = (commentDrafts[taskId] || '').trim();
    if (!text) return;
    const res = await fetch(`${API_BASE}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ text, task_id: taskId }),
    });
    if (res.ok) {
      setCommentDrafts((prev) => ({ ...prev, [taskId]: '' }));
      void fetchTasks();
    }
  };

  // LOGIKA ZA PROFIL - SLIKA
  const handleProfilePicUpload = async (e) => {
      e.preventDefault();
      if (!profileFile) return;
      const formData = new FormData();
      formData.append('file', profileFile);
      const res = await fetch(`${API_BASE}/users/me/profile-pic`, {
          method: 'POST',
          headers: authHeaders(),
          body: formData
      });
      if (res.ok) {
          setProfileMessage({text: 'Profil fotoğrafı güncellendi.', type: 'success'});
          setProfileFile(null);
          if(profileFileRef.current) profileFileRef.current.value = "";
          fetchUserData();
      } else {
          setProfileMessage({text: 'Fotoğraf yüklenemedi.', type: 'error'});
      }
  };

  const handleProfilePicDelete = async () => {
      const res = await fetch(`${API_BASE}/users/me/profile-pic`, {
          method: 'DELETE',
          headers: authHeaders()
      });
      if (res.ok) {
          setProfileMessage({text: 'Profil fotoğrafı silindi.', type: 'success'});
          fetchUserData();
      }
  };

  // LOGIKA ZA PROFIL - LOZINKA
  const handlePasswordChange = async (e) => {
      e.preventDefault();
      setPassMessage({text:'', type:''});
      if(newPass !== confirmNewPass) {
          setPassMessage({text: 'Yeni şifreler eşleşmiyor!', type: 'error'});
          return;
      }
      const issues = getPasswordIssues(newPass);
      if(issues.length > 0) {
          setPassMessage({text: 'Şifre zayıf. Kuralları kontrol edin.', type: 'error'});
          return;
      }
      const res = await fetch(`${API_BASE}/users/me/change-password`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json', ...authHeaders()},
          body: JSON.stringify({
              old_password: oldPass,
              new_password: newPass,
              confirm_password: confirmNewPass
          })
      });
      if(res.ok) {
          setPassMessage({text: 'Şifreniz başarıyla değiştirildi!', type: 'success'});
          setOldPass(''); setNewPass(''); setConfirmNewPass('');
      } else {
          const errMsg = await readError(res, 'Şifre değiştirilemedi.');
          setPassMessage({text: errMsg, type: 'error'});
      }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setTasksList([]); setUserData(null); setCurrentView('login');
  };

  const currentPasswordIssues = getPasswordIssues(regPassword);
  const newPasswordIssues = getPasswordIssues(newPass);

  const filteredTasks = tasksList.filter((t) => {
    if (filterPriority !== 'All' && t.priority !== filterPriority) return false;
    if (filterStatus !== 'All' && t.status !== filterStatus) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const inText = (t.title || '').toLowerCase().includes(q) || (t.description || '').toLowerCase().includes(q);
      const inAssignee = (t.assigned_to || '').toLowerCase().includes(q);
      if (!inText && !inAssignee) return false;
    }
    return true;
  });

  const tasksByStatus = {
    'To-Do': filteredTasks.filter((t) => t.status === 'To-Do'),
    'In-Progress': filteredTasks.filter((t) => t.status === 'In-Progress' || !t.status),
    'Completed': filteredTasks.filter((t) => t.status === 'Completed'),
  };

  return (
    <div className="app-container">
      <Toaster position="bottom-right" reverseOrder={false} />   
      <div className="theme-toggle-wrapper">
        <button className="toggle-btn" onClick={toggleTheme}>
          {isDarkMode ? '☀️ Aydınlık Mod' : '🌙 Karanlık Mod'}
        </button>
      </div>
      <h1 className="main-title">Görev Yöneticisi {/* Bağlantı durumu göstergesi eklendi */}
        {(currentView === 'dashboard' || currentView === 'profile') && (
          <span 
            title={isWsConnected ? "Gerçek zamanlı bağlı" : "Bağlantı koptu"}
            style={{
              display: 'inline-block',
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              marginLeft: '15px',
              backgroundColor: isWsConnected ? '#4caf50' : '#f44336'
            }}
          />
        )}</h1>

      {currentView === 'login' && (
        <div className="auth-card auth-panel">
          <div className="auth-top">
            <div>
              <h2>Giriş Yap</h2>
              <p className="muted-text">Yetkili erişim için kullanıcı adı/e-posta ve şifre girin.</p>
            </div>
          </div>
          {loginError && <div className="message-box error">{loginError}</div>}
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label>Kullanıcı Adı veya E-posta</label>
              <input className="form-input" value={loginIdentifier} onChange={(e) => setLoginIdentifier(e.target.value)} placeholder="Ad veya e-posta" />
            </div>
            <div className="form-group">
              <label>Şifre</label>
              <div className="field-with-toggle">
                <input type={loginShowPassword ? 'text' : 'password'} className="form-input" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} placeholder="Şifrenizi girin" />
                <button type="button" className="toggle-eye-btn" onClick={() => setLoginShowPassword((prev) => !prev)}>
                  {loginShowPassword ? '🔒' : '👁️'}
                </button>
              </div>
            </div>
            <button className="btn-primary">Giriş Yap</button>
          </form>
          <button type="button" className="link-button" onClick={() => setCurrentView('register')}>Kayıt Ol</button>
        </div>
      )}

      {currentView === 'register' && (
        <div className="auth-card auth-panel">
          <div className="auth-top">
            <div>
              <h2>Kayıt Ol</h2>
              <p className="muted-text">Şifre kuralları sistem tarafından kontrol edilir.</p>
            </div>
          </div>
          {regError && <div className="message-box error" style={{ whiteSpace: 'pre-line' }}>{regError}</div>}
          <form onSubmit={handleRegister}>
            <div className="form-group">
              <label>Kullanıcı Adı</label>
              <input className="form-input" value={regUsername} onChange={(e) => setRegUsername(e.target.value)} placeholder="Adınız" />
            </div>
            <div className="form-group">
              <label>E-posta</label>
              <input type="email" className="form-input" value={regEmail} onChange={(e) => setRegEmail(e.target.value)} placeholder="ornek@mail.com" />
            </div>
            <div className="form-group">
              <label>Şifre</label>
              <div className="field-with-toggle">
                <input type={showRegPass ? 'text' : 'password'} className="form-input" value={regPassword} onChange={(e) => setRegPassword(e.target.value)} placeholder="En az 8 karakter" />
                <button type="button" className="toggle-eye-btn" onClick={() => setShowRegPass((prev) => !prev)}>{showRegPass ? '🔒' : '👁️'}</button>
              </div>
              <div className="field-hint" style={{ marginTop: '8px', fontSize: '0.9em' }}>
                {regPassword.length > 0 && currentPasswordIssues.length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: '20px', color: '#d9534f' }}>
                    {currentPasswordIssues.map((issue, idx) => <li key={idx}>{issue}</li>)}
                  </ul>
                ) : regPassword.length === 0 ? (
                  <span style={{ color: '#6c757d' }}>{PASSWORD_POLICY}</span>
                ) : (
                  <span style={{ color: '#28a745', fontWeight: 'bold' }}>Şifre uygun!</span>
                )}
              </div>
            </div>
            <div className="form-group">
              <label>Şifre Tekrar</label>
              <div className="field-with-toggle">
                <input type={showConfirmPass ? 'text' : 'password'} className="form-input" value={regConfirmPassword} onChange={(e) => setRegConfirmPassword(e.target.value)} placeholder="Şifreyi tekrar girin" />
                <button type="button" className="toggle-eye-btn" onClick={() => setShowConfirmPass((prev) => !prev)}>{showConfirmPass ? '🔒' : '👁️'}</button>
              </div>
            </div>
            <button className="btn-primary">Kaydı Tamamla</button>
          </form>
          <button type="button" className="link-button" onClick={() => setCurrentView('login')}>Geri Dön</button>
        </div>
      )}

      {(currentView === 'dashboard' || currentView === 'profile') && (
        <div className="dashboard-wrapper">
          <nav className="nav-header">
            <div className="nav-buttons">
              <button onClick={() => setCurrentView('dashboard')} className={`nav-btn ${currentView === 'dashboard' ? 'active' : ''}`}>Panel</button>
              <button onClick={() => setCurrentView('profile')} className={`nav-btn ${currentView === 'profile' ? 'active' : ''}`}>Profilim</button>
            </div>
            <button onClick={logout} className="logout-btn">Çıkış Yap</button>
          </nav>

          {currentView === 'dashboard' ? (
            <>
              <div className="action-grid single-panel">
                <div className="action-box wide-box">
                  <h3>Yeni Görev</h3>
                  {taskMessage.text && <div className={`message-box ${taskMessage.type}`}>{taskMessage.text}</div>}
                  <form onSubmit={handleCreateTask}>
                    <div className="form-group">
                      <label>Başlık</label>
                      <input className="form-input" value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} placeholder="Görev başlığı" required/>
                    </div>
                    
                    <div style={{display:'flex', gap:'15px'}}>
                        <div className="form-group" style={{flex: 1}}>
                            <label>Öncelik (Priority)</label>
                            <select className="form-input" value={taskPriority} onChange={(e)=>setTaskPriority(e.target.value)}>
                                <option value="High">🔴 Yüksek (High)</option>
                                <option value="Normal">🟡 Normal</option>
                                <option value="Low">🟢 Düşük (Low)</option>
                            </select>
                        </div>
                        <div className="form-group" style={{flex: 1}}>
                            <label>Durum (Status)</label>
                            <select className="form-input" value={taskStatus} onChange={(e)=>setTaskStatus(e.target.value)}>
                                <option value="To-Do">📋 To-Do</option>
                                <option value="In-Progress">⚙️ In-Progress</option>
                                <option value="Completed">✅ Completed</option>
                            </select>
                        </div>
                        <div className="form-group" style={{flex: 1}}>
                            <label>Son Tarih (Deadline)</label>
                            <input type="date" className="form-input" value={taskDeadline} onChange={(e)=>setTaskDeadline(e.target.value)} />
                        </div>
                    </div>

                    <div className="form-group">
                      <label>Atanan Kişi (Assigned to)</label>
                      <input className="form-input" value={taskAssignedTo} onChange={(e) => setTaskAssignedTo(e.target.value)} placeholder="Örn: Jones, Smith" />
                    </div>

                    <div className="form-group">
                      <label>Açıklama</label>
                      <textarea className="form-input textarea" value={taskDesc} onChange={(e) => setTaskDesc(e.target.value)} placeholder="Görev detayları" required/>
                    </div>
                    <div className="form-group">
                      <label>Görev Görseli</label>
                      <input ref={taskFileRef} type="file" accept="image/*" onChange={(e) => setTaskFile(e.target.files?.[0] || null)} />
                    </div>
                    <button className="btn-primary">Görevi Kaydet</button>
                  </form>
                </div>
              </div>

              {stats && (
                <div className="stats-bar">
                  <div className="stat-chip"><span className="stat-num">{stats.total}</span><span className="stat-lbl">Toplam</span></div>
                  <div className="stat-chip"><span className="stat-num">{stats.by_status['To-Do'] || 0}</span><span className="stat-lbl">To-Do</span></div>
                  <div className="stat-chip"><span className="stat-num">{stats.by_status['In-Progress'] || 0}</span><span className="stat-lbl">In-Progress</span></div>
                  <div className="stat-chip"><span className="stat-num">{stats.by_status['Completed'] || 0}</span><span className="stat-lbl">Completed</span></div>
                  <div className="stat-chip warn"><span className="stat-num">{stats.overdue}</span><span className="stat-lbl">Süresi Geçti</span></div>
                  <div className="stat-chip ok"><span className="stat-num">{stats.completed_this_week}</span><span className="stat-lbl">Bu Hafta ✓</span></div>
                </div>
              )}

              <div className="tasks-toolbar">
                <input
                  className="form-input"
                  style={{ flex: 2, minWidth: 200 }}
                  placeholder="Ara: başlık, açıklama, atanan..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <select className="form-input" style={{ flex: 1, minWidth: 140 }} value={filterPriority} onChange={(e) => setFilterPriority(e.target.value)}>
                  <option value="All">Öncelik: Tümü</option>
                  <option value="High">🔴 High</option>
                  <option value="Normal">🟡 Normal</option>
                  <option value="Low">🟢 Low</option>
                </select>
                <select className="form-input" style={{ flex: 1, minWidth: 140 }} value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
                  <option value="All">Durum: Tümü</option>
                  <option value="To-Do">📋 To-Do</option>
                  <option value="In-Progress">⚙️ In-Progress</option>
                  <option value="Completed">✅ Completed</option>
                </select>
                <button className="nav-btn" onClick={handleExportTasks} title="JSON olarak dışa aktar">⬇ Export</button>
                <button className="nav-btn" onClick={() => importFileRef.current?.click()} title="JSON içe aktar">⬆ Import</button>
                <input ref={importFileRef} type="file" accept="application/json,.json" style={{ display: 'none' }} onChange={handleImportTasks} />
              </div>

              <div className="kanban-board">
                {(['To-Do', 'In-Progress', 'Completed']).map((col) => (
                  <div key={col} className={`kanban-column kanban-${col === 'Completed' ? 'done' : col === 'To-Do' ? 'todo' : 'prog'}`}>
                    <div className="kanban-header">
                      <span>{col === 'To-Do' ? '📋 To-Do' : col === 'In-Progress' ? '⚙️ In-Progress' : '✅ Completed'}</span>
                      <span className="kanban-count">{tasksByStatus[col].length}</span>
                    </div>
                    <div className="kanban-body">
                      {tasksByStatus[col].length === 0 ? (
                        <div className="empty-text" style={{ textAlign: 'center', padding: '20px' }}>Görev yok</div>
                      ) : tasksByStatus[col].map((t) => (
                        <div key={t.id} className="task-card">
                          {editingTaskId === t.id ? (
                            <div className="edit-container" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                              <div className="form-group">
                                <label style={{ fontSize: '0.8rem' }}>Başlığı Güncelle</label>
                                <input className="form-input" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
                              </div>
                              <div style={{ display: 'flex', gap: '10px' }}>
                                <div className="form-group" style={{ flex: 1 }}>
                                  <label style={{ fontSize: '0.8rem' }}>Öncelik</label>
                                  <select className="form-input" value={editPriority} onChange={(e) => setEditPriority(e.target.value)}>
                                    <option value="High">High</option>
                                    <option value="Normal">Normal</option>
                                    <option value="Low">Low</option>
                                  </select>
                                </div>
                                <div className="form-group" style={{ flex: 1 }}>
                                  <label style={{ fontSize: '0.8rem' }}>Durum</label>
                                  <select className="form-input" value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
                                    <option value="To-Do">To-Do</option>
                                    <option value="In-Progress">In-Progress</option>
                                    <option value="Completed">Completed</option>
                                  </select>
                                </div>
                                <div className="form-group" style={{ flex: 1 }}>
                                  <label style={{ fontSize: '0.8rem' }}>Son Tarih</label>
                                  <input type="date" className="form-input" value={editDeadline} onChange={(e) => setEditDeadline(e.target.value)} />
                                </div>
                              </div>
                              <div className="form-group">
                                <label style={{ fontSize: '0.8rem' }}>Atanan Kişi</label>
                                <input className="form-input" value={editAssignedTo} onChange={(e) => setEditAssignedTo(e.target.value)} />
                              </div>
                              <div className="form-group">
                                <label style={{ fontSize: '0.8rem' }}>Açıklamayı Güncelle</label>
                                <textarea className="form-input textarea" value={editDesc} onChange={(e) => setEditDesc(e.target.value)} />
                              </div>
                              <div style={{ display: 'flex', gap: '8px' }}>
                                <button className="btn-primary" style={{ flex: 1 }}
                                  onClick={() => {
                                    handleUpdateTask(t.id, {
                                      title: editTitle, description: editDesc, priority: editPriority,
                                      deadline: editDeadline || null, assigned_to: editAssignedTo, status: editStatus,
                                    });
                                    setEditingTaskId(null);
                                  }}>
                                  Kaydet (Sync)
                                </button>
                                <button className="btn-secondary" style={{ flex: 1, marginTop: 0 }} onClick={() => setEditingTaskId(null)}>İptal</button>
                              </div>
                            </div>
                          ) : (
                            <>
                              <div className="task-card-top">
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                                  <h4>#{t.id} - {t.title}</h4>
                                  <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                                    {t.priority && <span className={`badge priority-${t.priority.toLowerCase()}`}>{t.priority}</span>}
                                    {t.status && <span className={`badge status-${t.status === 'Completed' ? 'done' : t.status === 'To-Do' ? 'todo' : 'prog'}`}>{t.status}</span>}
                                  </div>
                                </div>
                                <div style={{ display: 'flex', gap: '5px' }}>
                                  <button className="nav-btn" style={{ minWidth: 'auto', padding: '5px 10px', fontSize: '0.8rem' }}
                                    onClick={() => {
                                      setEditingTaskId(t.id); setEditTitle(t.title); setEditDesc(t.description);
                                      setEditPriority(t.priority || 'Normal'); setEditStatus(t.status || 'In-Progress');
                                      setEditDeadline(t.deadline || ''); setEditAssignedTo(t.assigned_to || '');
                                    }}>
                                    Düzenle
                                  </button>
                                  <button className="btn-small-danger" onClick={() => handleDeleteTask(t.id)}>Sil</button>
                                </div>
                              </div>

                              {t.deadline && <p className="task-meta">📅 <strong>Son Tarih:</strong> {t.deadline}</p>}
                              {t.assigned_to && <p className="task-meta">👤 <strong>Atanan:</strong> {t.assigned_to}</p>}
                              {t.completed_at && <p className="task-meta">✅ <strong>Bitiş:</strong> {new Date(t.completed_at).toLocaleString()}</p>}

                              {t.image_url && <img src={formatUrl(t.image_url)} alt="Görev" className="task-image" />}
                              <p className="task-desc">{t.description}</p>

                              {t.status !== 'Completed' ? (
                                <button className="btn-success-outline" onClick={() => handleMarkCompleted(t)} style={{ marginTop: '10px', marginBottom: '10px' }}>
                                  ✔️ Tamamlandı İşaretle
                                </button>
                              ) : (
                                <button className="btn-secondary" onClick={() => handleReopenTask(t)} style={{ marginTop: '10px', marginBottom: '10px' }}>
                                  ↩ Yeniden Aç
                                </button>
                              )}

                              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '5px' }}>
                                Versiyon (T/D): {t.title_updated_at?.toFixed(2)} / {t.desc_updated_at?.toFixed(2)}
                              </div>

                              <div className="comments-section">
                                <span className="comments-title">Yorumlar</span>
                                <div className="existing-comments">
                                  {t.comments?.length > 0 ? t.comments.map(c => (
                                    <div key={c.id} className="comment-chip">{c.text}</div>
                                  )) : <span className="empty-text">Henüz yorum yok.</span>}
                                </div>
                                <div className="comment-input-wrapper">
                                  <input className="comment-input" placeholder="Yorum yaz..." value={commentDrafts[t.id] || ''} onChange={(e) => setCommentDrafts(prev => ({ ...prev, [t.id]: e.target.value }))} />
                                  <button className="btn-comment-add" onClick={() => handleAddComment(t.id)}>Ekle</button>
                                </div>
                              </div>
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            // PROFIL SEKCIJA (Tvoj sigurnosni zadatak)
            <div className="profile-grid">
              
              <div className="profile-card main-info" style={{display:'flex', flexDirection:'column', alignItems:'center'}}>
                <div className="profile-avatar-large">
                  {userData?.profile_pic ? <img src={formatUrl(userData.profile_pic)} className="profile-photo" alt="Profil" /> : <span>{userData?.username?.charAt(0).toUpperCase()}</span>}
                </div>
                <div className="info-list" style={{textAlign:'center'}}>
                  <p>Kullanıcı: <strong>{userData?.username}</strong></p>
                  <p>E-posta: <strong>{userData?.email}</strong></p>
                </div>

                <div style={{width:'100%', marginTop:'20px', borderTop:'1px solid var(--border-color)', paddingTop:'20px'}}>
                    <h4 style={{marginTop:0, textAlign:'center'}}>Profil Fotoğrafı Güncelle</h4>
                    {profileMessage.text && <div className={`message-box ${profileMessage.type}`}>{profileMessage.text}</div>}
                    <form onSubmit={handleProfilePicUpload} style={{display:'flex', flexDirection:'column', gap:'10px'}}>
                        <input type="file" accept="image/*" ref={profileFileRef} className="form-input" onChange={(e)=>setProfileFile(e.target.files[0])} />
                        <button className="btn-primary" type="submit">Yükle</button>
                    </form>
                    {userData?.profile_pic && (
                        <button className="btn-small-danger" style={{width:'100%', marginTop:'10px', padding:'12px'}} onClick={handleProfilePicDelete}>
                            Mevcut Fotoğrafı Sil
                        </button>
                    )}
                </div>
              </div>
              
              <div className="profile-card">
                  <h3 style={{marginTop:0}}>Şifre Değiştir</h3>
                  {passMessage.text && <div className={`message-box ${passMessage.type}`}>{passMessage.text}</div>}
                  <form onSubmit={handlePasswordChange}>
                      <div className="form-group">
                          <label>Eski Şifre</label>
                          <div className="field-with-toggle">
                              <input type={showOldPass ? 'text':'password'} className="form-input" value={oldPass} onChange={(e)=>setOldPass(e.target.value)} required/>
                              <button type="button" className="toggle-eye-btn" onClick={()=>setShowOldPass(!showOldPass)}>{showOldPass ? '🔒' : '👁️'}</button>
                          </div>
                      </div>
                      <div className="form-group">
                          <label>Yeni Şifre</label>
                          <div className="field-with-toggle">
                              <input type={showNewPass ? 'text':'password'} className="form-input" value={newPass} onChange={(e)=>setNewPass(e.target.value)} required/>
                              <button type="button" className="toggle-eye-btn" onClick={()=>setShowNewPass(!showNewPass)}>{showNewPass ? '🔒' : '👁️'}</button>
                          </div>
                      </div>
                      <div className="form-group">
                          <label>Yeni Şifre (Tekrar)</label>
                          <div className="field-with-toggle">
                              <input type={showConfirmNewPass ? 'text':'password'} className="form-input" value={confirmNewPass} onChange={(e)=>setConfirmNewPass(e.target.value)} required/>
                              <button type="button" className="toggle-eye-btn" onClick={()=>setShowConfirmNewPass(!showConfirmNewPass)}>{showConfirmNewPass ? '🔒' : '👁️'}</button>
                          </div>
                      </div>
                      <button type="submit" className="btn-primary">Şifreyi Güncelle</button>
                  </form>
              </div>

            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;

