/**
 * TypeScript interfaces for architecture code generation
 * Compatible with the Python models in architecture_code_models.py
 */

export enum CodeType {
  CLOUDFORMATION = 'cloudformation',
  TERRAFORM = 'terraform',
  KUBERNETES = 'kubernetes',
  CDK = 'cdk',
  PULUMI = 'pulumi'
}

export enum TargetPlatform {
  AWS = 'aws',
  KUBERNETES = 'kubernetes',
  MULTI_CLOUD = 'multi_cloud'
}

export enum FileType {
  INFRASTRUCTURE = 'infrastructure',
  APPLICATION = 'application',
  CONFIG = 'config',
  DOCUMENTATION = 'documentation'
}

export enum CodeGenerationStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export interface CodeGenerationRequest {
  architecture_description: string;
  diagram_metadata?: Record<string, any>;
  code_type?: CodeType;
  target_platform?: TargetPlatform;
  components?: string[];
  technologies?: string[];
  project_name?: string;
  output_directory?: string;
  include_documentation?: boolean;
  include_tests?: boolean;
}

export interface GeneratedCodeFile {
  filename: string;
  content: string;
  file_type: FileType;
  language: string;
  description?: string;
  dependencies?: string[];
  download_url?: string;
  file_size: number;
  relative_path: string;
  local_path?: string;
  created_at: string;
}

export interface CodeGenerationResponse {
  success: boolean;
  generated_files: GeneratedCodeFile[];
  directory_structure: Record<string, any>;
  project_name: string;
  project_id: string;
  zip_download_url?: string;
  local_directory?: string;
  error_message?: string;
  metadata: Record<string, any>;
  generated_at: string;
  total_files: number;
  total_size: number;
}

export interface DiagramWithCodeRequest {
  conversation_history: Array<Record<string, any>>;
  diagram_type?: string;
  code_generation_enabled?: boolean;
  code_type?: CodeType;
  target_platform?: TargetPlatform;
  project_name?: string;
  output_directory?: string;
}

export interface CodeGenerationJob {
  job_id: string;
  status: CodeGenerationStatus;
  request: CodeGenerationRequest;
  response?: CodeGenerationResponse;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  progress_percentage: number;
  current_step?: string;
}

// Frontend-specific interfaces
export interface CodeGenerationUIState {
  isGenerating: boolean;
  currentJob?: CodeGenerationJob;
  generatedProjects: CodeGenerationResponse[];
  selectedCodeType: CodeType;
  selectedPlatform: TargetPlatform;
  includeDocumentation: boolean;
  includeTests: boolean;
}

export interface CodeFileDisplayProps {
  file: GeneratedCodeFile;
  onDownload?: (file: GeneratedCodeFile) => void;
  onView?: (file: GeneratedCodeFile) => void;
}

export interface CodeGenerationFormProps {
  onSubmit: (request: CodeGenerationRequest) => void;
  isLoading?: boolean;
  initialValues?: Partial<CodeGenerationRequest>;
}

export interface ProjectDownloadProps {
  response: CodeGenerationResponse;
  onDownloadFile?: (file: GeneratedCodeFile) => void;
  onDownloadProject?: (response: CodeGenerationResponse) => void;
}