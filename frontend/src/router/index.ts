import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/projects',
    },
    {
      path: '/projects',
      name: 'ProjectList',
      component: () => import('@/views/ProjectList.vue'),
    },
    {
      path: '/projects/create',
      name: 'ProjectCreate',
      component: () => import('@/views/ProjectCreate.vue'),
    },
    {
      path: '/projects/:id',
      name: 'ProjectDetail',
      component: () => import('@/views/ProjectDetail.vue'),
    },
    {
      path: '/projects/:id/agents',
      name: 'AgentConfig',
      component: () => import('@/views/AgentConfig.vue'),
    },
    {
      path: '/projects/:id/tasks/create',
      name: 'TaskCreate',
      component: () => import('@/views/TaskCreate.vue'),
    },
    {
      path: '/tasks/:id/monitor',
      name: 'TaskMonitor',
      component: () => import('@/views/TaskMonitor.vue'),
    },
    {
      path: '/tasks/:id/review',
      name: 'TaskReview',
      component: () => import('@/views/TaskReview.vue'),
    },
  ],
})

export default router
