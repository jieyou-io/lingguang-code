import { createRouter, createWebHistory } from 'vue-router';
import Index from '@/pages/Index.vue';
import ChatPage from '@/pages/ChatPage.vue';
import ProjectsPage from '@/pages/ProjectsPage.vue';
import SessionsPage from '@/pages/SessionsPage.vue';
import StatsPage from '@/pages/StatsPage.vue';
import PluginsPage from '@/pages/PluginsPage.vue';
import SettingsPage from '@/pages/SettingsPage.vue';
import NotFound from '@/pages/NotFound.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: Index,
    },
    {
      path: '/sessions',
      component: SessionsPage,
    },
    {
      path: '/sessions/:projectId',
      component: SessionsPage,
      props: true,
    },
    {
      path: '/chat/:sessionId',
      component: ChatPage,
      props: true,
    },
    {
      path: '/chat/:projectId/:sessionId',
      component: ChatPage,
      props: true,
    },
    {
      path: '/chat/new',
      component: ChatPage,
    },
    {
      path: '/projects',
      component: ProjectsPage,
    },
    {
      path: '/stats',
      component: StatsPage,
    },
    {
      path: '/plugins',
      component: PluginsPage,
    },
    {
      path: '/settings',
      component: SettingsPage,
    },
    {
      path: '/:pathMatch(.*)*',
      component: NotFound,
    },
  ],
});

export default router;
