import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Avatar,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Chip,
  CircularProgress,
  Tooltip,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  Alert,
  LinearProgress,
  Card,
  CardContent,
  Badge
} from '@mui/material';
import {
  Send,
  ContentCopy,
  Psychology,
  Code,
  Analytics,
  SmartToy,
  Person,
  Add,
  History,
  Delete,
  AttachFile,
  Close,
  MoreVert,
  Archive,
  Refresh,
  Settings,
  TrendingUp,
  Chat,
  FileUpload,
  CheckCircle,
  Error as ErrorIcon
} from '@mui/icons-material';

const API_BASE_URL = 'http://localhost:8000/api';

const AK_GREEN = '#2aa411';
const AK_GREEN_DARK = '#1e7a0d';
const BG_DARK = '#000000';
const SURFACE = '#0e0e0e';
const SURFACE_2 = '#111315';
const BORDER = 'rgba(42, 164, 17, 0.25)';
const TEXT_PRIMARY = '#ffffff';
const TEXT_SECONDARY = '#cbd5e1';
const TEXT_MUTED = '#94a3b8';

/* === Added: capabilities list for sidebar === */
const AGENT_FEATURES = [
  { title: 'Marketing Strategist', desc: 'Synthesizes briefs & positioning from your goals and constraints.' },
  { title: 'Ad Generation', desc: 'Creates on-brand variations with Brand Guard checks.' },
  { title: 'Smart Invoice Generator', desc: 'Builds clean invoices and exports shareable PDFs.' },
  { title: 'Code Generation', desc: 'Drafts scripts, utilities, and boilerplate safely.' },
  { title: 'Dataset Analysis', desc: 'Summarizes data, surfaces insights, and charts.' },
];

const CodeBlock = ({ children, language = 'text' }) => {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = () => {
    navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Box sx={{ my: 2 }}>
      <Paper
        elevation={2}
        sx={{
          backgroundColor: '#0d1117',
          color: '#c9d1d9',
          borderRadius: 2,
          overflow: 'hidden',
          border: '1px solid #30363d'
        }}
      >
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            px: 2,
            py: 1,
            backgroundColor: '#161b22',
            borderBottom: '1px solid #30363d'
          }}
        >
          <Typography
            variant="caption"
            sx={{
              color: AK_GREEN, 
              fontWeight: 600,
              textTransform: 'uppercase',
              fontSize: '0.75rem'
            }}
          >
            {language}
          </Typography>
          <Tooltip title={copied ? "Copied!" : "Copy code"}>
            <IconButton
              size="small"
              onClick={handleCopy}
              sx={{
                color: '#8b949e',
                '&:hover': { backgroundColor: '#21262d', color: '#f0f6fc' }
              }}
            >
              <ContentCopy fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        <Box sx={{ p: 2 }}>
          <pre
            style={{
              margin: 0,
              fontFamily: 'JetBrains Mono, Consolas, Monaco, "Courier New", monospace',
              fontSize: '14px',
              lineHeight: 1.5,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}
          >
            {children}
          </pre>
        </Box>
      </Paper>
    </Box>
  );
};

// Agent Status Indicator
const AgentStatusIndicator = ({ agentName, status, size = 'small' }) => {
  const getAgentIcon = (name) => {
    switch(name) {
      case 'nlp_agent': return <Psychology />;
      case 'code_agent': return <Code />;
      case 'data_agent': return <Analytics />;
      default: return <SmartToy />;
    }
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'processing': return '#ff9800';
      case 'idle': return AK_GREEN; // brand green when idle
      case 'error': return '#f44336';
      default: return '#9e9e9e';
    }
  };

  return (
    <Tooltip title={`${agentName.replace('_agent', '')} Agent - ${status}`}>
      <Badge
        badgeContent=""
        color="primary"
        variant="dot"
        sx={{
          '& .MuiBadge-badge': {
            backgroundColor: getStatusColor(status),
            boxShadow: status === 'processing' ? '0 0 8px rgba(255, 152, 0, 0.6)' : 'none',
            animation: status === 'processing' ? 'pulse 1.5s ease-in-out infinite' : 'none'
          }
        }}
      >
        <Avatar
          sx={{
            width: size === 'large' ? 40 : 24,
            height: size === 'large' ? 40 : 24,
            backgroundColor: getStatusColor(status),
            color: '#000'
          }}
        >
          {getAgentIcon(agentName)}
        </Avatar>
      </Badge>
    </Tooltip>
  );
};

// Enhanced Message Formatting
const formatMessage = (content) => {
  const codeBlockRegex = /```(\w+)?\n([\s\S]*?)\n```/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: content.slice(lastIndex, match.index)
      });
    }
    
    parts.push({
      type: 'code',
      language: match[1] || 'text',
      content: match[2]
    });
    
    lastIndex = match.index + match[0].length;
  }
  
  if (lastIndex < content.length) {
    parts.push({
      type: 'text',
      content: content.slice(lastIndex)
    });
  }

  return parts.length > 0 ? parts : [{ type: 'text', content }];
};

const FileUploadDialog = ({ open, onClose, onFileUploaded }) => {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileUpload = async (file) => {
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const result = await response.json();
        onFileUploaded(result);
        onClose();
      } else {
        throw new Error('Upload failed');
      }
    } catch (error) {
      console.error('Upload error:', error);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ color: TEXT_PRIMARY, backgroundColor: SURFACE }}>Upload File</DialogTitle>
      <DialogContent sx={{ backgroundColor: SURFACE_2 }}>
        <Box
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          sx={{
            border: `2px dashed ${dragOver ? AK_GREEN : BORDER}`,
            borderRadius: 2,
            p: 4,
            textAlign: 'center',
            backgroundColor: dragOver ? 'rgba(42,164,17,0.06)' : SURFACE,
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            color: TEXT_SECONDARY
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          <FileUpload sx={{ fontSize: 48, color: AK_GREEN, mb: 2 }} />
          <Typography variant="h6" gutterBottom color={TEXT_PRIMARY}>
            Drop files here or click to browse
          </Typography>
          <Typography variant="body2" sx={{ color: TEXT_MUTED }}>
            Supports: .txt, .py, .js, .csv, .json, .md and more (Max 5MB)
          </Typography>
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
            style={{ display: 'none' }}
            accept=".txt,.py,.js,.csv,.json,.md,.html,.css,.xml,.pdf,.doc,.docx"
          />
        </Box>
        {uploading && (
          <Box sx={{ mt: 2 }}>
            <LinearProgress />
            <Typography variant="body2" sx={{ mt: 1, textAlign: 'center', color: TEXT_MUTED }}>
              Uploading and processing file...
            </Typography>
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ backgroundColor: SURFACE_2 }}>
        <Button onClick={onClose} sx={{ color: TEXT_PRIMARY }}>Cancel</Button>
      </DialogActions>
    </Dialog>
  );
};

function App() {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState([]);
  const [agentStatus, setAgentStatus] = useState({});
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const [sessionMenuAnchor, setSessionMenuAnchor] = useState(null);
  const [selectedSessionForMenu, setSelectedSessionForMenu] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    loadAgents();
    loadChatHistory();
    
    const statusInterval = setInterval(loadAgentStatus, 3000);
    return () => clearInterval(statusInterval);
  }, []);

  const loadAgents = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/agents`);
      const data = await response.json();
      setAgents(data.available_agents || []);
    } catch (error) {
      console.error('Error loading agents:', error);
    }
  };

  const loadAgentStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/agents/status`);
      const data = await response.json();
      setAgentStatus(data.real_time_status || {});
    } catch (error) {
      console.error('Error loading agent status:', error);
    }
  };

  const loadChatHistory = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat/history`);
      const data = await response.json();
      setSessions(data.sessions || []);
      
      // Load the most recent session if none selected
      if (!currentSessionId && data.sessions.length > 0) {
        setCurrentSessionId(data.sessions[0].session_id);
        loadSessionMessages(data.sessions[0].session_id);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  const loadSessionMessages = async (sessionId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat/session/${sessionId}`);
      const data = await response.json();
      setMessages(data.messages || []);
    } catch (error) {
      console.error('Error loading session messages:', error);
      setMessages([]);
    }
  };

  const createNewSession = () => {
    const newSessionId = `session_${Date.now()}`;
    setCurrentSessionId(newSessionId);
    setMessages([]);
    setUploadedFile(null);
    
    const newSession = {
      session_id: newSessionId,
      title: "New Chat",
      message_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    setSessions(prev => [newSession, ...prev]);
  };

  const selectSession = (sessionId) => {
    if (sessionId !== currentSessionId) {
      setCurrentSessionId(sessionId);
      loadSessionMessages(sessionId);
      setUploadedFile(null);
    }
  };

  const deleteSession = async (sessionId) => {
    try {
      await fetch(`${API_BASE_URL}/chat/session/${sessionId}`, {
        method: 'DELETE'
      });
      
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));
      
      if (currentSessionId === sessionId) {
        const remainingSessions = sessions.filter(s => s.session_id !== sessionId);
        if (remainingSessions.length > 0) {
          selectSession(remainingSessions[0].session_id);
        } else {
          createNewSession();
        }
      }
      
      setSnackbar({ open: true, message: 'Session deleted', severity: 'success' });
    } catch (error) {
      console.error('Error deleting session:', error);
      setSnackbar({ open: true, message: 'Error deleting session', severity: 'error' });
    }
  };

  const sendMessage = async () => {
    if (!message.trim() && !uploadedFile) return;
    
    setLoading(true);
    
    const formData = new FormData();
    formData.append('message', message || 'Analyze this file');
    formData.append('session_id', currentSessionId);
    if (uploadedFile) {
      formData.append('file_id', uploadedFile.file_id);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (data.success) {
        await loadSessionMessages(currentSessionId);
        
        // Update session list
        await loadChatHistory();
        
        setMessage('');
        setUploadedFile(null);
      } else {
        setSnackbar({ open: true, message: 'Error sending message', severity: 'error' });
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setSnackbar({ open: true, message: 'Connection error', severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleFileUploaded = (fileData) => {
    setUploadedFile(fileData);
    setSnackbar({ 
      open: true, 
      message: `File "${fileData.filename}" uploaded successfully`, 
      severity: 'success' 
    });
  };

  const handleSessionMenu = (event, sessionId) => {
    event.stopPropagation();
    setSessionMenuAnchor(event.currentTarget);
    setSelectedSessionForMenu(sessionId);
  };

  const closeSessionMenu = () => {
    setSessionMenuAnchor(null);
    setSelectedSessionForMenu(null);
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh', backgroundColor: BG_DARK }}>
      {/* Sidebar */}
      <Drawer
        variant="persistent"
        anchor="left"
        open={sidebarOpen}
        sx={{
          /* width changed: 320 -> 380 */
          width: 380,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            /* width changed: 320 -> 380 */
            width: 380,
            boxSizing: 'border-box',
            backgroundColor: BG_DARK,
            borderRight: `1px solid ${BORDER}`,
            color: TEXT_PRIMARY
          }
        }}
      >
        {/* Sidebar Header */}
        <Box sx={{ p: 2, borderBottom: `1px solid ${BORDER}` }}>
          <Typography variant="h6" sx={{ fontWeight: 600, color: TEXT_PRIMARY }}>
            Akcero-Agent AI
          </Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={createNewSession}
            fullWidth
            sx={{
              mt: 2,
              backgroundColor: AK_GREEN,
              '&:hover': { backgroundColor: AK_GREEN_DARK },
              color: '#000'
            }}
          >
            New Chat
          </Button>
        </Box>

        {/* Agent Status */}
        <Box sx={{ p: 2, borderBottom: `1px solid ${BORDER}` }}>
          <Typography variant="subtitle2" sx={{ mb: 1, color: TEXT_MUTED }}>
            Akcero Agents
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {agents.map((agent) => (
              <AgentStatusIndicator
                key={agent.name}
                agentName={agent.name}
                status={agentStatus[agent.name]?.status || 'idle'}
              />
            ))}
          </Box>
        </Box>

        {/* === Added: Capabilities list under Akcero Agents === */}
        <Box sx={{ p: 2, borderBottom: `1px solid ${BORDER}` }}>
          <Typography variant="subtitle2" sx={{ mb: 1, color: TEXT_MUTED }}>
            Capabilities
          </Typography>
          <List dense sx={{ pt: 0 }}>
            {AGENT_FEATURES.map((f) => (
              <ListItem key={f.title} sx={{ alignItems: 'flex-start', px: 0 }}>
                <ListItemText
                  primary={f.title}
                  secondary={f.desc}
                  primaryTypographyProps={{ sx: { color: TEXT_PRIMARY, fontWeight: 600 } }}
                  secondaryTypographyProps={{ sx: { color: TEXT_SECONDARY, mt: 0.25 } }}
                />
              </ListItem>
            ))}
          </List>
        </Box>

        {/* Chat History */}
        <Box sx={{ flex: 1, overflow: 'auto' }}>
          <Box sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ color: TEXT_MUTED, mb: 1 }}>
              Recent Chats
            </Typography>
          </Box>
          <List sx={{ pt: 0 }}>
            {sessions.map((session) => (
              <ListItem
                key={session.session_id}
                button
                selected={currentSessionId === session.session_id}
                onClick={() => selectSession(session.session_id)}
                sx={{
                  mx: 1,
                  borderRadius: 1,
                  mb: 0.5,
                  color: TEXT_PRIMARY,
                  '&.Mui-selected': {
                    backgroundColor: 'rgba(42,164,17,0.12)',
                    '&:hover': { backgroundColor: 'rgba(42,164,17,0.18)' }
                  },
                  '&:hover': { backgroundColor: 'rgba(255,255,255,0.04)' }
                }}
              >
                <ListItemIcon sx={{ color: TEXT_PRIMARY }}>
                  <Chat fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary={session.title}
                  secondary={`${session.message_count} messages`}
                  primaryTypographyProps={{
                    fontSize: '0.875rem',
                    fontWeight: currentSessionId === session.session_id ? 600 : 400,
                    color: TEXT_PRIMARY
                  }}
                  secondaryTypographyProps={{ fontSize: '0.75rem', color: TEXT_MUTED }}
                />
                <IconButton
                  size="small"
                  onClick={(e) => handleSessionMenu(e, session.session_id)}
                  sx={{ color: TEXT_PRIMARY }}
                >
                  <MoreVert fontSize="small" />
                </IconButton>
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>

      {/* Main Content */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Paper
          elevation={1}
          sx={{
            p: 2,
            backgroundColor: SURFACE,
            borderBottom: `1px solid ${BORDER}`,
            zIndex: 1,
            color: TEXT_PRIMARY
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'between' }}>
            <Typography variant="h6" sx={{ fontWeight: 600, color: TEXT_PRIMARY }}>
              {sessions.find(s => s.session_id === currentSessionId)?.title || 'New Chat'}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, ml: 'auto' }}>
              <Tooltip title="Upload File">
                <IconButton onClick={() => setUploadDialogOpen(true)} sx={{ color: TEXT_PRIMARY }}>
                  <AttachFile />
                </IconButton>
              </Tooltip>
              <Tooltip title="Refresh">
                <IconButton onClick={loadChatHistory} sx={{ color: TEXT_PRIMARY }}>
                  <Refresh />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
          
          {/* File Upload Indicator */}
          {uploadedFile && (
            <Box sx={{ mt: 1 }}>
              <Chip
                label={`📎 ${uploadedFile.filename}`}
                onDelete={() => setUploadedFile(null)}
                color="primary"
                variant="outlined"
                size="small"
                sx={{ borderColor: AK_GREEN, color: TEXT_PRIMARY }}
              />
            </Box>
          )}
        </Paper>

        {/* Messages Area */}
        <Box
          sx={{
            flex: 1,
            overflow: 'auto',
            p: 2,
            backgroundColor: BG_DARK
          }}
        >
          {messages.length === 0 ? (
            <Box
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                textAlign: 'center'
              }}
            >
              <SmartToy sx={{ fontSize: 64, color: TEXT_MUTED, mb: 2 }} />
              <Typography variant="h5" sx={{ color: TEXT_PRIMARY, mb: 1 }}>
                Welcome to Multi-Agent AI
              </Typography>
              <Typography variant="body1" sx={{ color: TEXT_MUTED, maxWidth: 400 }}>
                Start a conversation with our specialized AI agents. Upload files, ask questions,
                or request code generation and data analysis.
              </Typography>
            </Box>
          ) : (
            messages.map((msg) => (
              <Box key={msg.id} sx={{ mb: 3 }}>
                {msg.type === 'user' ? (
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <Paper
                      elevation={1}
                      sx={{
                        maxWidth: '70%',
                        p: 2,
                        backgroundColor: AK_GREEN,
                        color: '#000',
                        borderRadius: '18px 18px 4px 18px'
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <Person fontSize="small" />
                        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                          You
                        </Typography>
                      </Box>
                      <Typography sx={{ lineHeight: 1.6 }}>
                        {msg.content}
                      </Typography>
                    </Paper>
                  </Box>
                ) : (
                  <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
                    <Paper
                      elevation={1}
                      sx={{
                        maxWidth: '85%',
                        p: 2,
                        backgroundColor: SURFACE, 
                        borderRadius: '18px 18px 18px 4px',
                        border: `1px solid ${BORDER}`,
                        color: TEXT_PRIMARY
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <AgentStatusIndicator
                          agentName={msg.agent_used}
                          status={agentStatus[msg.agent_used]?.status || 'idle'}
                          size="small"
                        />
                        <Typography
                          variant="subtitle2"
                          sx={{
                            color: TEXT_PRIMARY,
                            fontWeight: 600,
                            textTransform: 'capitalize'
                          }}
                        >
                          {msg.agent_used?.replace('_agent', '')} Agent
                        </Typography>
                      </Box>
                      
                      <Box>
                        {formatMessage(msg.content).map((part, partIndex) => (
                          part.type === 'code' ? (
                            <CodeBlock key={partIndex} language={part.language}>
                              {part.content}
                            </CodeBlock>
                          ) : (
                            <ReactMarkdown
                              key={partIndex}
                              remarkPlugins={[remarkGfm]}
                              components={{
                                p: ({ children }) => (
                                  <Typography sx={{ color: '#d1d5db', lineHeight: 1.6, mb: 1 }}>
                                    {children}
                                  </Typography>
                                ),
                                strong: ({ children }) => (
                                  <Typography component="span" sx={{ fontWeight: 'bold', color: TEXT_PRIMARY }}>
                                    {children}
                                  </Typography>
                                ),
                                em: ({ children }) => (
                                  <Typography component="span" sx={{ fontStyle: 'italic', color: '#e5e7eb' }}>
                                    {children}
                                  </Typography>
                                ),
                                ul: ({ children }) => (
                                  <Box component="ul" sx={{ pl: 2, my: 1, color: '#d1d5db' }}>
                                    {children}
                                  </Box>
                                ),
                                li: ({ children }) => (
                                  <Typography component="li" sx={{ mb: 0.5, color: '#d1d5db' }}>
                                    {children}
                                  </Typography>
                                ),
                                h3: ({ children }) => (
                                  <Typography variant="h6" sx={{ fontWeight: 600, mt: 2, mb: 1, color: TEXT_PRIMARY }}>
                                    {children}
                                  </Typography>
                                ),
                                h2: ({ children }) => (
                                  <Typography variant="h5" sx={{ fontWeight: 600, mt: 2, mb: 1, color: TEXT_PRIMARY }}>
                                    {children}
                                  </Typography>
                                )
                              }}
                            >
                              {part.content}
                            </ReactMarkdown>
                          )
                        ))}

                      </Box>
                    </Paper>
                  </Box>
                )}
              </Box>
            ))
          )}
          
          {loading && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, justifyContent: 'center', my: 2 }}>
              <CircularProgress size={20} />
              <Typography variant="body2" sx={{ color: TEXT_MUTED }}>
                AI is processing your request...
              </Typography>
            </Box>
          )}
          
          <div ref={messagesEndRef} />
        </Box>

        {/* Input Area */}
        <Paper
          elevation={2}
          sx={{
            p: 2,
            backgroundColor: SURFACE,
            borderTop: `1px solid ${BORDER}`
          }}
        >
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
            <TextField
              fullWidth
              multiline
              maxRows={4}
              variant="outlined"
              placeholder="I'm here to help, how can I assist you today?"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={loading}
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: '24px',
                  backgroundColor: SURFACE_2,
                  color: TEXT_PRIMARY,
                  '& fieldset': { borderColor: BORDER },
                  '&:hover fieldset': { borderColor: AK_GREEN },
                  '&.Mui-focused fieldset': { borderColor: AK_GREEN }
                }
              }}
            />
            <Button
              variant="contained"
              onClick={sendMessage}
              disabled={loading || (!message.trim() && !uploadedFile)}
              sx={{
                borderRadius: '50%',
                minWidth: '56px',
                height: '56px',
                backgroundColor: AK_GREEN,
                color: '#000',
                '&:hover': { backgroundColor: AK_GREEN_DARK }
              }}
            >
              <Send />
            </Button>
          </Box>
        </Paper>
      </Box>

      {/* Dialogs and Menus */}
      <FileUploadDialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        onFileUploaded={handleFileUploaded}
      />

      <Menu
        anchorEl={sessionMenuAnchor}
        open={Boolean(sessionMenuAnchor)}
        onClose={closeSessionMenu}
        PaperProps={{ sx: { backgroundColor: SURFACE, color: TEXT_PRIMARY, border: `1px solid ${BORDER}` } }}
      >
        <MenuItem onClick={() => {
          deleteSession(selectedSessionForMenu);
          closeSessionMenu();
        }}>
          <Delete fontSize="small" sx={{ mr: 1 }} />
          Delete
        </MenuItem>
      </Menu>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>

      {/* Global Styles for Animations */}
      <style>
        {`
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }
        `}
      </style>
    </Box>
  );
}

export default App;
