/**
 * 项目文件相关 API
 */
import { get } from '../api';
import type { ProjectFileNode } from '@/types';

interface FileTreeResponse {
  files: ProjectFileNode[];
}

interface FileContentResponse {
  path: string;
  content: string;
  truncated: boolean;
  size: number;
}

export async function getProjectFileTree(
  projectPath: string,
  options?: { maxDepth?: number; maxFiles?: number; includeHidden?: boolean }
): Promise<ProjectFileNode[]> {
  const params = new URLSearchParams({
    project_path: projectPath,
    max_depth: String(options?.maxDepth ?? 4),
    max_files: String(options?.maxFiles ?? 3000),
    include_hidden: String(options?.includeHidden ?? false),
  });
  const response = await get<FileTreeResponse>(`/v1/projects/files/tree?${params.toString()}`);
  return response.files || [];
}

export async function getProjectFileContent(
  projectPath: string,
  filePath: string,
  maxBytes = 200000
): Promise<FileContentResponse> {
  const params = new URLSearchParams({
    project_path: projectPath,
    file_path: filePath,
    max_bytes: String(maxBytes),
  });
  return get<FileContentResponse>(`/v1/projects/files/content?${params.toString()}`);
}
