import React, { useState } from 'react';
import { LogIn, User, Lock, ArrowRight } from 'lucide-react';
import { login } from '../utils/auth';
import { t, getLanguageCode, Language } from '../utils/translations';

interface LoginPageProps {
  onLogin: (user: { username: string; name: string; surname: string }) => void;
  onSwitchToSignup: () => void;
  language?: string;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLogin, onSwitchToSignup, language = 'English' }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const langCode = getLanguageCode(language);
  const translate = (key: string) => t(key, langCode);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const user = await login(username, password);
      if (user) {
        onLogin(user);
      } else {
        setError(translate('invalidCredentials'));
      }
    } catch (err) {
      setError(translate('loginFailed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-lightBg flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <img 
            src="https://activat.vc/themes/activat-vc/assets/images/logo.svg" 
            alt="Activat VC" 
            className="h-12"
          />
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl border border-borderLight shadow-soft p-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-activatBlue/10 rounded-xl">
              <LogIn className="w-6 h-6 text-activatBlue" />
            </div>
            <h1 className="text-2xl font-bold text-textMain">{translate('welcomeBack')}</h1>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div>
              <label className="block text-sm font-medium text-textMain mb-2">
                {translate('username')}
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slateGrey">
                  <User size={18} />
                </div>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="w-full pl-10 pr-4 py-3 border border-borderLight rounded-xl focus:outline-none focus:ring-2 focus:ring-activatBlue focus:border-transparent"
                  placeholder={translate('enterUsername')}
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-textMain mb-2">
                {translate('password')}
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slateGrey">
                  <Lock size={18} />
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full pl-10 pr-4 py-3 border border-borderLight rounded-xl focus:outline-none focus:ring-2 focus:ring-activatBlue focus:border-transparent"
                  placeholder={translate('enterPassword')}
                />
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm">
                {error}
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-activatBlue text-white font-semibold py-3 px-6 rounded-xl hover:bg-blue-600 transition-all duration-200 flex items-center justify-center gap-2 shadow-md shadow-activatBlue/20 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                translate('loggingIn')
              ) : (
                <>
                  {translate('signIn')}
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          {/* Switch to Signup */}
          <div className="mt-6 text-center">
            <p className="text-sm text-slateGrey">
              {translate('dontHaveAccount')}{' '}
              <button
                onClick={onSwitchToSignup}
                className="text-activatBlue font-medium hover:underline"
              >
                {translate('signUp')}
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
