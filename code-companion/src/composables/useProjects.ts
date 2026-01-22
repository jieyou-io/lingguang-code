/**
 * 项目数据管理 Composable
 */
import { ref, computed } from 'vue';
import { getClaudeProjects, getProjectStats } from '@/lib/services/projects';
import type { Project } from '@/types';

export function useProjects() {
  const projects = ref<Project[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  /**
   * 加载项目数据
   */
  async function loadProjects() {
    loading.value = true;
    error.value = null;

    try {
      // 并行获取项目列表和统计数据
      const [backendProjects, projectStats] = await Promise.all([
        getClaudeProjects(),
        getProjectStats(),
      ]);

      // 将后端数据转换为前端格式
      projects.value = backendProjects.map((bp) => {
        // 从统计数据中查找对应项目的统计信息
        const stats = projectStats.find(
          (ps) => ps.project_path === bp.path || ps.project_name === bp.id
        );

        return {
          id: bp.id,
          name: bp.id, // 使用项目 ID 作为名称
          path: bp.path,
          lastActive: new Date(bp.created_at * 1000), // Unix 时间戳转换为毫秒
          activeSessions: bp.sessions.length,
          totalTokens: stats?.total_tokens || 0,
          totalCost: stats?.total_cost || 0,
        } as Project;
      });
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载项目失败';
      console.error('Failed to load projects:', err);
    } finally {
      loading.value = false;
    }
  }

  return {
    projects,
    loading,
    error,
    loadProjects,
  };
}
