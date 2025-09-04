// Home Page Component
// Main dashboard with welcome message and quick actions

import { useAuth } from '@/components/auth/AuthContext';
import { ROUTES } from '@/types/routes';
import { motion } from 'framer-motion';
import { Brain, FileText, MessageCircle, Sparkles, TrendingUp, Users } from 'lucide-react';
import React from 'react';

export const HomePage: React.FC = () => {
  const { authState } = useAuth();

  const quickActions = [
    {
      title: 'Start Chatting',
      description: 'Ask questions about your team\'s documentation',
      icon: MessageCircle,
      href: ROUTES.CHAT,
      color: 'from-purple-500 to-pink-500'
    },
    {
      title: 'Upload Documents',
      description: 'Add new documents to the knowledge base',
      icon: FileText,
      href: ROUTES.DOCUMENTS_UPLOAD,
      color: 'from-blue-500 to-cyan-500'
    },
    {
      title: 'Browse Documents',
      description: 'View and manage your document library',
      icon: Brain,
      href: ROUTES.DOCUMENTS,
      color: 'from-green-500 to-emerald-500'
    }
  ];

  const features = [
    {
      icon: Brain,
      title: 'AI-Powered Answers',
      description: 'Get instant, contextual responses powered by Claude AI models'
    },
    {
      icon: Sparkles,
      title: 'Smart Document Processing',
      description: 'Automatic text extraction and semantic indexing with Amazon Bedrock'
    },
    {
      icon: TrendingUp,
      title: 'Continuous Learning',
      description: 'Knowledge base improves as you add more team documentation'
    }
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Welcome Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center space-y-4"
      >
        <h1 className="text-4xl lg:text-6xl font-bold bg-gradient-to-r from-white via-purple-200 to-pink-200 bg-clip-text text-transparent">
          Welcome back{authState.user?.email ? `, ${authState.user.email.split('@')[0]}` : ''}!
        </h1>
        <p className="text-xl text-white/70 max-w-2xl mx-auto">
          Your AI-powered development assistant is ready to help you find answers from your team's knowledge base.
        </p>
      </motion.div>

      {/* User Info Card */}
      {authState.user && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="backdrop-blur-xl bg-white/10 border border-white/20 rounded-2xl p-6"
        >
          <div className="flex items-center space-x-4">
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-r from-purple-500 to-pink-500">
              <Users className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">Account Information</h3>
              <div className="flex items-center space-x-4 text-sm text-white/70">
                <span>Email: {authState.user.email}</span>
                <span>•</span>
                <span className="capitalize">Role: {authState.user['custom:role']}</span>
                {authState.user['custom:department'] && (
                  <>
                    <span>•</span>
                    <span>Department: {authState.user['custom:department']}</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.6 }}
        className="space-y-6"
      >
        <h2 className="text-2xl font-bold text-white">Quick Actions</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {quickActions.map((action, index) => (
            <motion.a
              key={action.title}
              href={action.href}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + index * 0.1, duration: 0.6 }}
              whileHover={{ scale: 1.05, y: -5 }}
              whileTap={{ scale: 0.95 }}
              className="block backdrop-blur-xl bg-white/10 border border-white/20 rounded-2xl p-6 hover:bg-white/20 transition-all duration-300 group"
            >
              <div className={`inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-r ${action.color} shadow-lg mb-4 group-hover:scale-110 transition-transform`}>
                <action.icon className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">{action.title}</h3>
              <p className="text-white/70">{action.description}</p>
            </motion.a>
          ))}
        </div>
      </motion.div>

      {/* Features Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.6 }}
        className="space-y-6"
      >
        <h2 className="text-2xl font-bold text-white">Powered by AWS</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 + index * 0.1, duration: 0.6 }}
              className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6"
            >
              <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-white/10 mb-4">
                <feature.icon className="w-5 h-5 text-purple-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
              <p className="text-white/60">{feature.description}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Getting Started */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7, duration: 0.6 }}
        className="backdrop-blur-xl bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-500/30 rounded-2xl p-8 text-center"
      >
        <h2 className="text-2xl font-bold text-white mb-4">Ready to get started?</h2>
        <p className="text-white/70 mb-6 max-w-2xl mx-auto">
          Upload your team's documentation and start asking questions. The AI will learn from your content and provide accurate, contextual answers.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <motion.a
            href={ROUTES.DOCUMENTS_UPLOAD}
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold rounded-xl shadow-lg transition-all duration-200"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            Upload Documents
          </motion.a>
          <motion.a
            href={ROUTES.CHAT}
            className="px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/20 text-white font-semibold rounded-xl transition-all duration-200"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            Start Chatting
          </motion.a>
        </div>
      </motion.div>
    </div>
  );
};