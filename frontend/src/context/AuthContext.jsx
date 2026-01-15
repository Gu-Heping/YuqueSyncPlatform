import api from '../api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUser = async () => {
    try {
      const response = await api.get('/auth/users/me');
      setUser(response.data);
    } catch (error) {
      console.error("Failed to fetch user", error);
      // Only clear token if 401 (handled by api interceptor mostly, but safe to keep logic)
      if (error.response?.status === 401) {
        localStorage.removeItem('token');
      }
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const response = await api.post('/auth/login', formData);
    const { access_token } = response.data;

    localStorage.setItem('token', access_token);
    await fetchUser();
    return true;
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    // Optional: Redirect to login is handled by components or router
  };

  const updateProfile = async (data) => {
    const response = await api.put('/auth/users/me', data);
    setUser(response.data);
    return response.data;
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, updateProfile }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
