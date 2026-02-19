import React, { useState } from 'react';
import { UserPlus, User, Lock, Mail, ArrowRight } from 'lucide-react';
import { signup, userExists } from '../utils/auth';
import { t, getLanguageCode, Language } from '../utils/translations';

interface SignupPageProps {
  onSignup: (user: { id: number; username: string; name: string; surname: string }) => void;
  onSwitchToLogin: () => void;
  language?: string;
}

export const SignupPage: React.FC<SignupPageProps> = ({ onSignup, onSwitchToLogin, language = 'English' }) => {
  const [username, setUsername] = useState('');
  const [name, setName] = useState('');
  const [surname, setSurname] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const langCode = getLanguageCode(language);
  const translate = (key: string) => t(key, langCode);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError(translate('passwordsNotMatch'));
      return;
    }

    if (password.length < 6) {
      setError(translate('passwordTooShort'));
      return;
    }

    setLoading(true);

    try {
      const exists = await userExists(username);
      if (exists) {
        setError(translate('usernameExists'));
        setLoading(false);
        return;
      }

      const user = await signup(username, name, surname, password);
      if (user) {
        onSignup({ id: user.id, username: user.username, name: user.name, surname: user.surname });
      } else {
        setError(translate('signupFailed'));
      }
    } catch (err) {
      setError(translate('signupFailed'));
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

        {/* Signup Card */}
        <div className="bg-white rounded-2xl border border-borderLight shadow-soft p-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-activatBlue/10 rounded-xl">
              <UserPlus className="w-6 h-6 text-activatBlue" />
            </div>
            <h1 className="text-2xl font-bold text-textMain">{translate('createAccount')}</h1>
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
                  placeholder={translate('chooseUsername')}
                />
              </div>
            </div>

            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-textMain mb-2">
                {translate('name')}
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full px-4 py-3 border border-borderLight rounded-xl focus:outline-none focus:ring-2 focus:ring-activatBlue focus:border-transparent"
                placeholder={translate('enterName')}
              />
            </div>

            {/* Surname */}
            <div>
              <label className="block text-sm font-medium text-textMain mb-2">
                {translate('surname')}
              </label>
              <input
                type="text"
                value={surname}
                onChange={(e) => setSurname(e.target.value)}
                required
                className="w-full px-4 py-3 border border-borderLight rounded-xl focus:outline-none focus:ring-2 focus:ring-activatBlue focus:border-transparent"
                placeholder={translate('enterSurname')}
              />
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
                  placeholder={translate('createPassword')}
                />
              </div>
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-sm font-medium text-textMain mb-2">
                {translate('confirmPassword')}
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slateGrey">
                  <Lock size={18} />
                </div>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  className="w-full pl-10 pr-4 py-3 border border-borderLight rounded-xl focus:outline-none focus:ring-2 focus:ring-activatBlue focus:border-transparent"
                  placeholder={translate('confirmPasswordPlaceholder')}
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
                translate('creatingAccount')
              ) : (
                <>
                  {translate('createAccount')}
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          {/* Switch to Login */}
          <div className="mt-6 text-center">
            <p className="text-sm text-slateGrey">
              {translate('alreadyHaveAccount')}{' '}
              <button
                onClick={onSwitchToLogin}
                className="text-activatBlue font-medium hover:underline"
              >
                {translate('signIn')}
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
