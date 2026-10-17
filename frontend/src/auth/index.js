import { config } from '@/config'
import { azureProvider } from './azureProvider'
import { localProvider } from './localProvider'

export const authProvider = config.authMode === 'azure' ? azureProvider : localProvider
